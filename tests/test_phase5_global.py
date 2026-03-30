import json
from dotenv import load_dotenv

load_dotenv()
from src.scoring.global_scorer import GlobalScientificScorer

def main():
    print("="*80)
    print("🏁 ISOLATION TEST STRICT : PHASE 5 (GLOBAL SCORER & SYNTHÈSE)")
    print("="*80)

    # Simulation parfaite de l'état du Graphe (MatchingState)
    mock_state = {
        "candidate_id": "CANDIDATE_AHMED_SAAD",
        "job_description": "Principal Manufacturing Engineer. Requires full-scale production optimization.",
        "raw_text_data": {
            "pitch": "I am a PhD candidate specializing in interfaces. I have not worked in a factory but I know ISO 13485."
        },
        "tech_analysis": [
            {"skill_name": "ISO 13485", "status": "FOUND", "audit_status": "VALIDATED", "proof_excerpt": "ISO 13485 used in lab."}
        ],
        # Résultats des branches parallèles (format final actuel)
        "psychometrics": {
            "job_alignment_score": 7.5  # Bon fit, mais un peu académique
        },
        "rhetoric_analysis": {
            "communication_score": 8.0  # Parle très bien (STAR method)
        },
        "logistics_analysis": {
            "global_feasibility_score": 5.0  # NO_GO : Il ne veut pas faire ce métier
        }
    }

    # Exécution de la synthèse
    global_scorer = GlobalScientificScorer()
    final_report = global_scorer.finalize_matching_report(mock_state)

    # Affichage du Rapport Exécutif
    print("\n" + "⭐"*40)
    print(f" 🎯 FINAL READINESS SCORE : {final_report['score_out_of_10']} / 10.0")
    print(f" 🚀 EQUIVALENT TRL LEVEL  : {final_report['readiness_level']} / 9.0")
    print("⭐"*40)

    print("\n📊 PONDÉRATION DES DIMENSIONS :")
    for dim, score in final_report['dimensions'].items():
        print(f"   • {dim:<26} : {score}/10")

    print(f"\n📝 VERDICT DU CTO :\n{final_report['expert_verdict']}")

    print("\n📉 JSON FINAL PRÊT POUR LE FRONT-END :")
    # Affiche un extrait du JSON
    print(json.dumps(final_report['dimensions'], indent=2))

if __name__ == "__main__":
    main()
