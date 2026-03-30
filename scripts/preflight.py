import argparse
import importlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def check_python() -> tuple[int, int]:
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) >= (3, 10):
        _ok(f"Python {major}.{minor} compatible.")
        return 0, 0
    _fail(f"Python {major}.{minor} detecte. Version minimale requise: 3.10")
    return 1, 0


def check_project_files() -> tuple[int, int]:
    required = [
        "app.py",
        "requirements.txt",
        "run_phase1_ingestion.py",
        "reindex.py",
        "src",
        "ui",
        "data",
    ]
    critical = 0
    for rel in required:
        path = PROJECT_ROOT / rel
        if path.exists():
            _ok(f"Present: {rel}")
        else:
            _fail(f"Manquant: {rel}")
            critical += 1
    return critical, 0


def check_imports() -> tuple[int, int]:
    modules = [
        "streamlit",
        "pandas",
        "openpyxl",
        "langgraph",
        "langchain",
        "langchain_core",
        "langchain_groq",
        "langchain_community",
        "presidio_analyzer",
        "presidio_anonymizer",
        "spacy",
        "docling.document_converter",
        "langdetect",
        "rank_bm25",
        "faiss",
        "neo4j",
        "cryptography",
    ]
    critical = 0
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            _ok(f"Import: {module_name}")
        except Exception as exc:
            _fail(f"Import KO: {module_name} ({exc})")
            critical += 1
    return critical, 0


def check_env() -> tuple[int, int]:
    warnings = 0
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        _ok(".env detecte.")
    else:
        _warn(".env absent. Copier .env.example vers .env puis renseigner les cles.")
        warnings += 1

    groq = os.getenv("GROQ_API_KEY", "").strip()
    neo4j_pwd = os.getenv("NEO4J_PASSWORD", "").strip()
    if groq:
        _ok("GROQ_API_KEY detectee.")
    else:
        _warn("GROQ_API_KEY absente (les agents LLM peuvent echouer).")
        warnings += 1

    if neo4j_pwd:
        _ok("NEO4J_PASSWORD detecte.")
    else:
        _warn("NEO4J_PASSWORD absent (Neo4j peut echouer).")
        warnings += 1

    return 0, warnings


def check_spacy_models() -> tuple[int, int]:
    warnings = 0
    try:
        import spacy.util
    except Exception as exc:
        _warn(f"spaCy indisponible pour verif modeles ({exc})")
        return 0, 1

    has_en = spacy.util.is_package("en_core_web_lg") or spacy.util.is_package("en_core_web_sm")
    has_fr = spacy.util.is_package("fr_core_news_md") or spacy.util.is_package("fr_core_news_sm")

    if has_en:
        _ok("Modele spaCy EN detecte.")
    else:
        _warn("Aucun modele spaCy EN detecte (Presidio peut passer en degrade).")
        warnings += 1

    if has_fr:
        _ok("Modele spaCy FR detecte.")
    else:
        _warn("Aucun modele spaCy FR detecte (analyse FR degradee).")
        warnings += 1

    return 0, warnings


def check_neo4j() -> tuple[int, int]:
    try:
        from neo4j import GraphDatabase
    except Exception as exc:
        _warn(f"neo4j driver indisponible ({exc})")
        return 0, 1

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    if not password:
        _warn("Neo4j check saute: NEO4J_PASSWORD manquant.")
        return 0, 1

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5)
        driver.verify_connectivity()
        _ok(f"Neo4j connectivite OK ({uri}).")
        driver.close()
        return 0, 0
    except Exception as exc:
        _warn(f"Neo4j non joignable ({uri}): {exc}")
        return 0, 1


def main() -> int:
    parser = argparse.ArgumentParser(description="AEBM preflight checks")
    parser.add_argument(
        "--skip-neo4j",
        action="store_true",
        help="Skip Neo4j connectivity check.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run essentials only (python/files/imports/env).",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")

    print("=" * 64)
    print("AEBM PREFLIGHT - Diagnostic d'environnement")
    print("=" * 64)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Python exec : {sys.executable}")
    print("-" * 64)

    critical = 0
    warnings = 0

    for check in (check_python, check_project_files, check_imports, check_env):
        c, w = check()
        critical += c
        warnings += w

    if not args.quick:
        c, w = check_spacy_models()
        critical += c
        warnings += w

    if (not args.quick) and (not args.skip_neo4j):
        c, w = check_neo4j()
        critical += c
        warnings += w

    print("-" * 64)
    print(f"Resultat: critical={critical} | warnings={warnings}")
    if critical > 0:
        _fail("Preflight KO: corriger les erreurs critiques avant execution.")
        return 1
    _ok("Preflight OK: environnement executable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
