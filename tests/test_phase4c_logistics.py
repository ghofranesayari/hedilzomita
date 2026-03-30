import json
from pathlib import Path
from src.agents.logistics.preference import PreferenceAgent

def load_specific_candidate(candidate_id: str) -> dict:
    proc_dir = Path("data/processed")
    if not proc_dir.exists():
        print(f"⚠️ Le dossier {proc_dir} n'existe pas. Assurez-vous d'être à la racine du projet.")
        return {}
        
    for file in proc_dir.iterdir():
        if file.suffix == '.json' and candidate_id in file.name:
            print(f"👤 Candidat chargé : {file.name}")
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
    raise FileNotFoundError(f"❌ Le candidat '{candidate_id}' est introuvable.")

def main():
    print("="*70)
    print("🚩 ISOLATION TEST STRICT : PHASE 4C (AGENT LOGISTIQUE / DEALBREAKER)")
    print("="*70)

    # L'ID de votre candidat Ahmed Saad
    ID_DU_CANDIDAT = "CANDIDATE_66269BCD" 

    # 1. Chargement des vraies données du candidat
    try:
        cand_data = load_specific_candidate(ID_DU_CANDIDAT)
    except FileNotFoundError as e:
        print(e)
        return

    # Extraction des préférences réelles
    candidate_prefs = cand_data.get("preferences", {})
    if not candidate_prefs:
        print("❌ Aucune section 'preferences' trouvée dans le JSON du candidat.")
        return

    # 2. Métadonnées de NOTRE vraie offre d'emploi
    # Offre : "Principal-Manufacturing-Process-Engineer_8.27.2020.pdf"
    job_metadata_real = {
        "title": "Principal Manufacturing/Process Engineer",
        "industry": "Medical Devices", # Industrie de l'offre
        "salary_max": 120000.0, # Estimation réaliste pour un poste "Principal"
        "company_name": "Johnson & Johnson" # Test pour voir s'il détecte la cible du candidat
    }

    # 3. Lancement de l'Agent
    print("\n--- TEST SUR VRAIES DONNÉES (Ahmed Saad vs Principal Engineer) ---")
    logistics_agent = PreferenceAgent()
    result = logistics_agent.evaluate_feasibility(candidate_prefs, job_metadata_real)

    # 4. Affichage du résultat
    print(f"\n⭐ SCORE DE FAISABILITÉ : {result['global_feasibility_score']} / 10")
    print(f"⚖️ RECOMMANDATION DÉCISIONNELLE : {result['decision_recommendation']}")
    print("-" * 50)
    for flag in result['flags']:
        # Met des emojis pour une belle UI
        icon = "✅" if flag['status'] == 'MATCH' else "⚠️" if flag['status'] in ['WARNING', 'INFO'] else "❌" if flag['status'] == 'MISMATCH' else "🚀"
        print(f"{icon} [{flag['category']}] : {flag['details']}")

if __name__ == "__main__":
    main()