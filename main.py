import os
import json
from pathlib import Path
import warnings

# Désactive certains warnings verbeux des librairies sous-jacentes
warnings.filterwarnings("ignore")

# Imports de nos modules
from src.ingestion.parser import ContentParser
from src.memory.hyde import HydeGenerator
from src.memory.vector_db import VectorDBManager
from src.orchestration.graph import AEBMGraphOrchestrator
from src.utils.visualizer import generate_radar_chart
from src.scoring.report import ReportGenerator

def get_job_offer() -> str:
    """Charge l'offre d'emploi depuis data/raw_jobs (En attendant l'upload manuel UI)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    job_dir = os.path.join(base_dir, "data", "raw_jobs")
    files = [f for f in os.listdir(job_dir) if f.endswith(('.pdf', '.docx', '.txt')) and not f.startswith('~')]
    
    if not files:
        raise FileNotFoundError(" Aucune offre trouvée dans data/raw_jobs/")
    
    target_path = os.path.join(job_dir, files[0])
    print(f"\n Lecture de l'Offre Cible : {files[0]}")
    return ContentParser().parse_pdf(Path(target_path))

def load_candidate_json(candidate_id: str) -> dict:
    """Charge le JSON du candidat depuis data/processed/."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "processed", f"{candidate_id}.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    print("="*60)
    print(" DÉMARRAGE DU PIPELINE COMPLET AEBM V5 (RAG + DAG)")
    print("="*60)

    # --- ÉTAPE 0 : SETUP NEO4J ---
    from src.memory.graph_store import GraphStore
    print(" Initialisation du Graphe Neo4j...")
    gs = GraphStore()
    gs.setup_database()
    gs.initialize_ontology()
    gs.close()
    
    # ... le reste du code main.py ne change pas ...

    # --- ÉTAPE 1 : RÉCUPÉRATION DE L'OFFRE ---
    job_text = get_job_offer()

    # --- ÉTAPE 2 : LE FILTRE VECTORIEL (SHORTLIST) ---
    print("\n PHASE 2 : Filtrage Vectoriel (FAISS)...")
    hyde = HydeGenerator()
    query_vector_text = hyde.generate_hypothetical_cvs(job_text)
    
    vdb = VectorDBManager()
    # On demande les 3 meilleurs candidats
    shortlist = vdb.search(query_vector_text, k=3) 
    
    if not shortlist:
        print(" FAISS n'a trouvé aucun candidat. Arrêt.")
        return

    print(f" Shortlist générée : {[c['candidate_id'] for c in shortlist]}")

    # --- ÉTAPE 3 : INITIALISATION DE L'ORCHESTRATEUR ---
    orchestrator = AEBMGraphOrchestrator()
    report_gen = ReportGenerator()

    # --- ÉTAPE 4 : LA BOUCLE D'AUDIT (CANDIDAT PAR CANDIDAT) ---
    for rank, cand_meta in enumerate(shortlist, 1):
        cand_id = cand_meta['candidate_id']
        real_name = report_gen.get_real_name(cand_id)
        print("\n" + "#"*60)
        print(f" ANALYSE DU CANDIDAT {rank}/3 : {real_name} ({cand_id})")
        print("#"*60)

        # Chargement des données brutes du candidat
        cand_data = load_candidate_json(cand_id)
        
        # Préparation de l'état initial pour LangGraph
        initial_state = {
            "candidate_id": cand_id,
            "job_description": job_text,
            "raw_text_data": {
                "cv": cand_data.get("cv_text", ""),
                "pitch": cand_data.get("pitch_text", ""),
                "clarify": cand_data.get("clarify_text", {})
            },
            "preferences_data": cand_data.get("preferences", {})
        }

        # Définition du Thread ID (Obligatoire pour la mémoire/pause LangGraph)
        thread_id = f"thread_{cand_id}"

        # 4.1 Exécution du graphe jusqu'au Breakpoint (interrupt_before="final_scoring")
        state = orchestrator.run_pipeline(initial_state, thread_id)
        
        # --- HUMAN IN THE LOOP (L'OPTION A) ---
        print("\n [PAUSE SYSTÈME - HUMAN IN THE LOOP]")
        print("Les agents ont terminé leurs analyses.")
        
        # On lit l'état actuel depuis la mémoire de LangGraph
        config = {"configurable": {"thread_id": thread_id}}
        current_state = orchestrator.app.get_state(config).values
        
        errors = current_state.get("system_errors", [])
        if errors:
            print(f" {len(errors)} erreur(s) détectée(s) : {errors}")
        else:
            print(" Toutes les branches ont convergé sans erreur.")

        # L'utilisateur doit valider
        input(f" Appuyez sur [ENTRÉE] pour autoriser le Scientific Scorer à rendre son verdict...")

        # 4.2 Reprise de l'exécution (On relance avec 'None' en input pour dire 'continue')
        print(" Reprise de l'exécution (Scoring final)...")
        final_state = orchestrator.run_pipeline(None, thread_id)
        
        # --- ÉTAPE 5 : GÉNÉRATION DES LIVRABLES ---
        print("\n GÉNÉRATION DES LIVRABLES...")
        
        # 5.1 Génération du Rapport Markdown
        report_path = report_gen.generate_markdown_report(final_state)
        
        # 5.2 Génération du Radar Chart
        diagnostic = final_state.get("readiness_diagnostic", {})
        dimensions = diagnostic.get("dimensions", {})
        if dimensions:
            generate_radar_chart(dimensions, cand_id)
        else:
            print(" Impossible de générer le Radar Chart (Dimensions manquantes).")

    print("\n CAMPAGNE TERMINÉE. Consultez le dossier 'outputs/' pour les résultats.")

if __name__ == "__main__":
    main()