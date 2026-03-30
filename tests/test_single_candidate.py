import os
import json
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

from src.ingestion.parser import ContentParser
from src.orchestration.graph import AEBMGraphOrchestrator
from src.utils.visualizer import generate_radar_chart
from src.scoring.report import ReportGenerator
from src.memory.graph_store import GraphStore

def get_job_offer() -> str:
    """Charge la première offre d'emploi depuis data/raw_jobs."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    job_dir = os.path.join(base_dir, "data", "raw_jobs")
    
    if not os.path.exists(job_dir):
        raise FileNotFoundError(f" Le dossier {job_dir} n'existe pas.")
        
    files = [f for f in os.listdir(job_dir) if f.endswith(('.pdf', '.docx', '.txt')) and not f.startswith('~')]
    
    if not files:
        raise FileNotFoundError(" Aucune offre trouvée dans data/raw_jobs/")
    
    target_path = os.path.join(job_dir, files[2])
    print(f" Offre cible chargée : {files[2]}")
    return ContentParser().parse_pdf(Path(target_path))

def get_specific_candidate(target_id: str = None) -> dict:
    """Récupère un candidat spécifique (ou le premier trouvé par défaut)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processed_dir = os.path.join(base_dir, "data", "processed")
    
    if not os.path.exists(processed_dir):
        raise FileNotFoundError(f" Le dossier {processed_dir} n'existe pas.")
        
    files = [f for f in os.listdir(processed_dir) if f.endswith('.json')]
    if not files:
        raise FileNotFoundError(" Aucun candidat JSON trouvé dans data/processed/")
    
    target_candidate = files[3]
    if target_id:
        for f in files:
            if target_id in f:
                target_candidate = f
                break
                
    print(f"👤 Candidat sélectionné pour le test : {target_candidate}")
    
    with open(os.path.join(processed_dir, target_candidate), 'r', encoding='utf-8') as f:
        return json.load(f)

def run_single_test():
    print("="*80)
    print(" MODE TEST : PIPELINE COMPLET SUR 1 SEUL CANDIDAT (RAG + DAG V5)")
    print("="*80)

    # --- ÉTAPE 0 : SETUP NEO4J ---
    print(" Initialisation du Graphe Neo4j...")
    try:
        gs = GraphStore()
        gs.setup_database()
        gs.initialize_ontology()
        gs.close()
    except Exception as e:
        print(f" Attention : Impossible de se connecter à Neo4j ({e}). Le test continue sans Graphe.")

    # --- ÉTAPE 1 : PRÉPARATION DES DONNÉES ---
    job_text = get_job_offer()
    # On force le test sur Ahmed Saad pour voir le "Ruthless CTO" en action
    cand_data = get_specific_candidate("CANDIDATE_66269BCD") 
    cand_id = cand_data["candidate_id"]

    # --- ÉTAPE 2 : INITIALISATION LANGGRAPH ---
    print("\n Chargement de l'Orchestrateur LangGraph...")
    orchestrator = AEBMGraphOrchestrator()
    report_gen = ReportGenerator()
    real_name = report_gen.get_real_name(cand_id)

    # Préparation de l'état initial (Structure stricte V5)
    initial_state = {
        "candidate_id": cand_id,
        "job_description": job_text,
        "raw_text_data": {
            "cv": cand_data.get("cv_text", ""),
            "pitch": cand_data.get("pitch_text", ""),
            "clarify": cand_data.get("clarify_text", {}) # Désormais bien un dictionnaire !
        },
        "preferences_data": cand_data.get("preferences", {})
    }

    thread_id = f"test_thread_{cand_id}"

    print("\n" + "#"*80)
    print(f" DÉBUT DE L'AUDIT SOUVERAIN : {real_name} ({cand_id})")
    print("#"*80)

    # --- ÉTAPE 3 : EXÉCUTION JUSQU'AU BREAKPOINT ---
    orchestrator.run_pipeline(initial_state, thread_id)
    
    # --- HUMAN IN THE LOOP ---
    print("\n [PAUSE SYSTÈME - HUMAN IN THE LOOP]")
    print("Les agents (Bridge, Psycho, Rhetoric, Logistics) ont terminé leurs analyses parallèles (Fan-Out).")
    
    # Vérification des erreurs dans la mémoire du graphe
    config = {"configurable": {"thread_id": thread_id}}
    current_state = orchestrator.app.get_state(config).values
    errors = current_state.get("system_errors", [])
    
    if errors:
        print(f" {len(errors)} erreur(s) détectée(s) : {errors}")
    else:
        print(" Toutes les branches ont convergé sans erreur critique.")

    input(f"\n Appuyez sur [ENTRÉE] pour déclencher le Ruthless CTO (Phase 5) et générer les livrables...")

    # --- ÉTAPE 4 : REPRISE ET GÉNÉRATION DES RAPPORTS ---
    print("\n Reprise de l'exécution (Scoring final)...")
    final_state = orchestrator.run_pipeline(None, thread_id)
    
    # Sécurité au cas où run_pipeline renverrait None après un resume
    if not final_state:
        final_state = orchestrator.app.get_state(config).values

    print("\n GÉNÉRATION DES LIVRABLES...")
    
    # 4.1 Génération Markdown Exécutif
    report_path = report_gen.generate_markdown_report(final_state)
    
    # 4.2 Génération Radar Chart HD
    diagnostic = final_state.get("readiness_diagnostic", {})
    dimensions = diagnostic.get("dimensions", {})
    if dimensions:
        # Sauvegarde dans outputs/reports/ pour que l'image accompagne le markdown
        generate_radar_chart(dimensions, cand_id, output_dir="outputs/reports/")
    else:
        print(" Radar Chart ignoré (données de dimensions manquantes).")

    print(f"\n TEST TERMINÉ AVEC SUCCÈS.")
    print(f"Consultez le dossier 'outputs/reports/' pour lire le rapport de {real_name} et voir son Radar Chart.")

if __name__ == "__main__":
    run_single_test()