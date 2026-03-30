from src.schemas.state import MatchingState

def node_aggregator(state: MatchingState) -> MatchingState:
    """
    Nœud de synchronisation (Fan-In).
    Il s'assure que toutes les branches parallèles ont bien livré leurs résultats.
    Il prépare le terrain pour le Scientific Scorer.
    """
    print("\n🔗 --- NODE: AGGREGATOR (Fusion des Données) ---")
    
    # 1. Récupération des résultats des branches
    tech_data = state.get("tech_analysis", [])
    psycho_data = state.get("psychometrics", {})
    rhetoric_data = state.get("rhetoric_analysis", {})
    logistics_data = state.get("logistics_analysis", {})
    
    # 2. Vérification d'Intégrité (Sanity Check)
    errors = []
    
    # Check Tech
    if not tech_data:
        errors.append(" Tech: Aucune compétence validée (Bridge/Auditor silent).")
    
    # Check Psycho
    if not psycho_data or "job_alignment_score" not in psycho_data:
        errors.append("Psycho: Échec de l'analyse (Score manquant).")
        # Fallback pour éviter le crash du Scorer
        state["psychometrics"] = {"job_alignment_score": 0.0, "summary": "Analyse échouée."}
        
    # Check Rhetoric
    if not rhetoric_data or "communication_score" not in rhetoric_data:
        errors.append(" Rhetoric: Échec de l'analyse STAR.")
        state["rhetoric_analysis"] = {"communication_score": 0.0, "feedback_summary": "Non disponible."}

    # Check Logistics
    if not logistics_data:
        errors.append(" Logistics: Échec de l'analyse des préférences.")
        state["logistics_analysis"] = {"global_feasibility_score": 0.0, "flags": []}

    # 3. Affichage du Bilan Intermédiaire
    print(f"    Intégrité des données : {' OK' if not errors else ' ALERTES'}")
    for err in errors:
        print(f"      {err}")
    
    # On ajoute les erreurs au state pour que le rapport final puisse les mentionner
    state["system_errors"] = errors
    
    return state