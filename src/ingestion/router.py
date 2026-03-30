import os
from pathlib import Path
from datetime import datetime
from langdetect import detect
import json
import re
from typing import Dict
from src.ingestion.pii_guard import PIIGuard
from src.ingestion.parser import ContentParser, load_excel_db
from src.schemas.candidate import CandidateDigitalTwin

class SmartRouter:
    def __init__(self, raw_data_path: str, output_path: str, excel_path: str):
        self.raw_path = Path(raw_data_path)
        self.output_path = Path(output_path)
        self.excel_db = load_excel_db(excel_path)
        
        self.parser = ContentParser()
        self.pii_guard = PIIGuard()
        
        self.output_path.mkdir(parents=True, exist_ok=True)

    # AJOUT DE 'self' ICI 👇
    def segment_clarify_document(self, text: str) -> Dict[str, str]:
        """
        Découpe le document Clarify en sections spécifiques pour la Fusion Granulaire.
        Utilise des Regex robustes pour tolérer les variations de formatage.
        """
        segments = {
            "ikigai": "",
            "ideal_day": "",
            "smart_goals": ""
        }

        if not text:
            return segments

        # --- REGEX ROBUSTES ---
        # Cherche "Question #1", "Question 1", "Q1", avec ou sans Markdown (##, **)
        pattern_q1 = re.compile(r'(?i)(?:##\s*|\*\*\s*|^)(?:Question\s*#?\s*1|Q1)[^\n]*\n(.*?)', re.DOTALL)
        pattern_q2 = re.compile(r'(?i)(?:##\s*|\*\*\s*|^)(?:Question\s*#?\s*2|Q2)[^\n]*\n(.*?)', re.DOTALL)
        pattern_q3 = re.compile(r'(?i)(?:##\s*|\*\*\s*|^)(?:Question\s*#?\s*3|Q3)[^\n]*\n(.*?)', re.DOTALL)
        pattern_q4 = re.compile(r'(?i)(?:##\s*|\*\*\s*|^)(?:Question\s*#?\s*4|Q4)[^\n]*\n(.*?)', re.DOTALL)

        # Extraction Q1 (Ikigai) -> De Q1 à Q2
        match_q1 = pattern_q1.search(text)
        match_q2 = pattern_q2.search(text)
        match_q3 = pattern_q3.search(text)
        match_q4 = pattern_q4.search(text)

        # On coupe le texte selon ce qu'on a trouvé
        if match_q1:
            end_idx = match_q2.start() if match_q2 else len(text)
            segments["ikigai"] = text[match_q1.end():end_idx].strip()
        
        if match_q2:
            end_idx = match_q3.start() if match_q3 else (match_q4.start() if match_q4 else len(text))
            segments["ideal_day"] = text[match_q2.end():end_idx].strip()

        if match_q4:
            # On prend tout de Q4 jusqu'à la fin
            segments["smart_goals"] = text[match_q4.end():].strip()

        # --- FALLBACK DE SÉCURITÉ ---
        # Si la regex n'a rien trouvé (formatage catastrophique du candidat)
        # On évite le crash en envoyant des morceaux arbitraires
        if not segments["ikigai"] and not segments["smart_goals"]:
            print("    ⚠️ Segmentation Clarify échouée : Mode Fallback activé.")
            parts = text.split("\n\n")
            total = len(parts)
            if total > 0:
                segments["ikigai"] = " ".join(parts[:max(1, total//3)])
                segments["ideal_day"] = " ".join(parts[max(1, total//3) : max(2, (2*total)//3)])
                segments["smart_goals"] = " ".join(parts[max(2, (2*total)//3):])

        return segments

    def _find_excel_row(self, candidate_name: str):
        """Logique floue pour trouver le candidat dans l'Excel via son nom de dossier."""
        # Nettoyage: "candidate_Ahmed Saad" -> "Ahmed Saad"
        clean_name = candidate_name.replace("candidate_", "").replace("_", " ").strip().lower()
        
        # Recherche dans l'Excel (On suppose une colonne 'Name' ou 'Email')
        # Vous devrez peut-être ajuster la colonne cible
        for idx, row in self.excel_db.iterrows():
            # Essai simple: Check si le nom est dans la ligne (concaténée)
            row_str = str(row.values).lower()
            if clean_name in row_str:
                return row
        
        print(f"⚠️ Attention: Pas de données Excel trouvées pour '{clean_name}'")
        return None

    def process_batch(self):
        print(f"🚀 Démarrage de l'ingestion depuis {self.raw_path}")
        
        # Itérer sur les dossiers "candidate_X"
        for candidate_dir in self.raw_path.iterdir():
            if not candidate_dir.is_dir() or "candidate_" not in candidate_dir.name:
                continue

            print(f"   📂 Traitement: {candidate_dir.name}")
            
            # 1. Identifier les fichiers (PDF ou DOCX)
            files = {"cv": None, "pitch": None, "clarify": None}
            
            # MODIFICATION ICI : On regarde tout ce qui est fichier
            for file in candidate_dir.iterdir():
                fname = file.name.lower()
                # On vérifie si c'est une extension supportée
                if not file.suffix.lower() in ['.pdf', '.docx', '.doc']:
                    continue

                # Logique de tri
                if "resume" in fname or "cv" in fname:
                    files["cv"] = file
                elif "pitch" in fname:
                    files["pitch"] = file
                elif "clarify" in fname:
                    files["clarify"] = file
            
            # 2. Parsing Textuel
            raw_texts = {}
            for key, fpath in files.items():
                if fpath:
                    raw_texts[key] = self.parser.parse_pdf(fpath)
                else:
                    raw_texts[key] = ""
                    print(f"      ❌ Manquant: {key}")

            # 3. Parsing Excel
            excel_row = self._find_excel_row(candidate_dir.name)
            prefs_data = self.parser.parse_excel_row(excel_row) if excel_row is not None else None
            
            # Si pas de préférences, on crée un objet vide pour ne pas casser le code
            if not prefs_data:
                from src.schemas.candidate import PreferenceData
                prefs_data = PreferenceData()

            # 4. Anonymisation & ID
            # On utilise le nom du dossier comme "Vrai Nom"
            real_name = candidate_dir.name.replace("candidate_", "").replace("_", " ")
            anon_id = self.pii_guard.get_or_create_candidate_id(real_name)
            
            # Anonymisation des textes
            clean_cv = self.pii_guard.anonymize_text(raw_texts["cv"])
            clean_pitch = self.pii_guard.anonymize_text(raw_texts["pitch"])
            clean_clarify_raw = self.pii_guard.anonymize_text(raw_texts["clarify"])

            # 4.5 DECOUPAGE CHIRURGICAL (Le Fix)
            # On découpe le texte anonymisé
            # 4.5 DECOUPAGE CHIRURGICAL
            segmented_clarify = self.segment_clarify_document(clean_clarify_raw)

            # 5. Détection Langue (sur le CV)
            try:
                lang = detect(clean_cv) if len(clean_cv) > 50 else "en"
            except:
                lang = "en"

            # 6. Création Digital Twin
            twin = CandidateDigitalTwin(
                candidate_id=anon_id,
                original_filename_id=candidate_dir.name,
                language=lang,
                ingestion_date=datetime.now().isoformat(),
                cv_text=clean_cv,
                pitch_text=clean_pitch,
                clarify_text=segmented_clarify, # INJECTION DU DICTIONNAIRE ICI
                preferences=prefs_data
            )

            # 7. Sauvegarde JSON
            out_file = self.output_path / f"{anon_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(twin.model_dump_json(indent=2))
            
            print(f"      ✅ Sauvegardé: {out_file.name}")
    
    

    