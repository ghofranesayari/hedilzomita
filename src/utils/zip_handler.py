# src/utils/zip_handler.py
import zipfile
import os
import shutil
from pathlib import Path
from src.ingestion.router import SmartRouter

def process_b2b_zip(uploaded_zip, temp_dir="data/temp_b2b"):
    """Extrait le ZIP, lance l'ingestion et retourne le chemin des JSON générés."""
    raw_dir = os.path.join(temp_dir, "raw")
    processed_dir = os.path.join(temp_dir, "processed")
    
    # Nettoyage des anciens dossiers temporaires
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    # 1. Extraction du ZIP
    with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
        zip_ref.extractall(raw_dir)

    # 2. Lancement du SmartRouter sur ce dossier temporaire
    # On simule un fichier Excel vide s'il n'y en a pas
    dummy_excel = os.path.join(temp_dir, "dummy.xlsx")
    import pandas as pd
    pd.DataFrame().to_excel(dummy_excel)

    print(" B2B : Lancement de l'ingestion Docling/Presidio...")
    router = SmartRouter(raw_data_path=raw_dir, output_path=processed_dir, excel_path=dummy_excel)
    router.process_batch()

    return processed_dir