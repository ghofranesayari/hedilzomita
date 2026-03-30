import json
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover
    Fernet = None
    InvalidToken = Exception


class PIIGuard:
    def __init__(self, vault_path: str = "data/vault/vault.json"):
        self.vault_path = Path(vault_path)
        try:
            self.analyzer = AnalyzerEngine()
            self._presidio_ready = True
        except Exception as exc:
            # Keep ingestion alive even in offline environments.
            print(f"[PII] Presidio indisponible ({exc}). Mode regex de secours active.")
            self.analyzer = None
            self._presidio_ready = False

        self.anonymizer = AnonymizerEngine()
        self._fernet = self._init_cipher()
        self.vault = self._load_vault()
        self._plaintext_warning_emitted = False

    def _init_cipher(self):
        """Initialize vault encryption key.

        Priority:
        1) PII_VAULT_KEY environment variable (recommended).
        2) PII_VAULT_KEY_PATH file.
        3) Auto-generated local key file near vault (first run).
        """
        if Fernet is None:
            print("[PII] cryptography non disponible. Vault non chiffre (degrade mode).")
            return None

        key_env = os.getenv("PII_VAULT_KEY", "").strip()
        key_path = Path(
            os.getenv(
                "PII_VAULT_KEY_PATH",
                str(self.vault_path.with_suffix(".key")),
            )
        )

        try:
            if key_env:
                return Fernet(key_env.encode("utf-8"))

            if key_path.exists():
                key_bytes = key_path.read_bytes().strip()
                return Fernet(key_bytes)

            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_bytes = Fernet.generate_key()
            key_path.write_bytes(key_bytes)
            try:
                os.chmod(key_path, 0o600)
            except OSError:
                pass
            print(f"[PII] Nouvelle cle de vault generee: {key_path}")
            return Fernet(key_bytes)
        except Exception as exc:
            print(f"[PII] Echec init chiffrement vault: {exc}. Mode degrade (non chiffre).")
            return None

    def _load_vault(self) -> Dict[str, str]:
        """Load vault mapping ID -> real name.

        Supports:
        - Legacy plaintext mapping format.
        - Encrypted wrapper format (fernet_v1).
        """
        if not self.vault_path.exists():
            return {}

        try:
            payload = json.loads(self.vault_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[PII] Vault illisible: {exc}")
            return {}

        if not isinstance(payload, dict):
            return {}

        if payload.get("vault_format") == "fernet_v1":
            if not self._fernet:
                print("[PII] Vault chiffre detecte mais aucune cle disponible.")
                return {}
            token = str(payload.get("ciphertext", ""))
            if not token:
                return {}
            try:
                clear = self._fernet.decrypt(token.encode("utf-8"))
                data = json.loads(clear.decode("utf-8"))
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
            except InvalidToken:
                print("[PII] Cle vault invalide. Mapping identites non charge.")
                return {}
            except Exception as exc:
                print(f"[PII] Echec decryption vault: {exc}")
                return {}
            return {}

        # Legacy plaintext mapping
        return {str(k): str(v) for k, v in payload.items()}

    def _save_vault(self) -> None:
        """Persist vault mapping securely when possible."""
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

        if self._fernet:
            clear = json.dumps(self.vault, ensure_ascii=False).encode("utf-8")
            token = self._fernet.encrypt(clear).decode("utf-8")
            wrapper = {
                "vault_format": "fernet_v1",
                "ciphertext": token,
            }
            self.vault_path.write_text(
                json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return

        if not self._plaintext_warning_emitted:
            print("[PII] Attention: vault sauvegarde en clair (mode degrade).")
            self._plaintext_warning_emitted = True

        self.vault_path.write_text(
            json.dumps(self.vault, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_or_create_candidate_id(self, real_name: str) -> str:
        """Return stable anonymized candidate ID for a given real name."""
        clean_name = real_name.lower().strip()
        for anon_id, name in self.vault.items():
            if name.lower().strip() == clean_name:
                return anon_id

        new_id = f"CANDIDATE_{uuid.uuid4().hex[:8].upper()}"
        self.vault[new_id] = real_name.strip()
        self._save_vault()
        return new_id

    def _analyze_multilingual(self, text: str) -> List:
        """Run Presidio on FR + EN and merge detections."""
        if not self.analyzer:
            return []

        entities = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION"]
        merged = {}

        for lang in ("fr", "en"):
            try:
                results = self.analyzer.analyze(text=text, entities=entities, language=lang)
            except Exception:
                continue
            for r in results:
                key = (r.start, r.end, r.entity_type)
                prev = merged.get(key)
                if prev is None or float(getattr(r, "score", 0.0)) > float(
                    getattr(prev, "score", 0.0)
                ):
                    merged[key] = r

        ordered = sorted(merged.values(), key=lambda x: (x.start, x.end))
        return ordered

    @staticmethod
    def _regex_fallback_anonymize(text: str) -> str:
        """Last-resort anonymization when Presidio is unavailable."""
        anonymized = text
        anonymized = re.sub(
            r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
            "<EMAIL>",
            anonymized,
        )
        anonymized = re.sub(
            r"(?:(?:\+?\d{1,3}[\s\-\.]?)?(?:\(?\d{2,4}\)?[\s\-\.]?)\d{2,4}[\s\-\.]?\d{2,4}(?:[\s\-\.]?\d{2,4})?)",
            "<PHONE>",
            anonymized,
        )
        return anonymized

    def anonymize_text(self, text: str) -> str:
        """Replace sensitive entities with safe placeholders."""
        if not text:
            return ""

        results = self._analyze_multilingual(text)
        if not results:
            return self._regex_fallback_anonymize(text)

        try:
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                    "PERSON": OperatorConfig("replace", {"new_value": "<CANDIDATE_NAME>"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                    "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
                },
            )
            return anonymized_result.text
        except Exception as exc:
            print(f"[PII] Echec anonymisation Presidio ({exc}). Fallback regex applique.")
            return self._regex_fallback_anonymize(text)
