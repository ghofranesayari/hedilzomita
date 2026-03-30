import os
from src.ingestion.router import SmartRouter

def run_ingestion():
    # Définition des chemins absolus
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Le chemin corrigé vers les dossiers des candidats (batch_01)
    RAW_CANDIDATES_DIR = os.path.join(BASE_DIR, "data", "raw", "batch_01") 
    
    # 2. Le dossier de sortie des JSON
    PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
    
    # 3. Le chemin exact vers votre fichier Excel
    EXCEL_PATH = os.path.join(BASE_DIR, "data", "raw", "form_data", "candidates_intake_form.xlsx") 

    print(" DÉMARRAGE RE-INGESTION (PHASE 1)...")
    print(f"📁 Source Candidats : {RAW_CANDIDATES_DIR}")
    print(f"📊 Source Excel     : {EXCEL_PATH}")
    
    # Initialisation du SmartRouter
    router = SmartRouter(
        raw_data_path=RAW_CANDIDATES_DIR,
        output_path=PROCESSED_DIR,
        excel_path=EXCEL_PATH
    )
    
    # Lancement du traitement
    router.process_batch()
    
    print("\n Ingestion terminée ! Les nouveaux JSON structurés sont générés.")

if __name__ == "__main__":
    run_ingestion()