import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from src.scoring.scientific_scorer import ScientificScorer



def main():
    print("="*80)
    print("🏆 ISOLATION TEST STRICT : PHASE 5 (SCIENTIFIC SCORER V5.1)")
    print("="*80)

    # 1. SIMULATION INPUT 1 : Liste stricte des Hard Skills validés
    mock_tech_analysis = [
        {"skill_name": "ISO 13485", "status": "FOUND", "audit_status": "VALIDATED", "proof_excerpt": "Testing standards (ASTM, ISO 13485)"},
        {"skill_name": "Customer Discovery", "status": "FOUND", "audit_status": "VALIDATED", "proof_excerpt": "Conducted over 50 customer interviews"},
        {"skill_name": "Polymer modifications", "status": "FOUND", "audit_status": "VALIDATED", "proof_excerpt": "implant surface modifications"}
    ]

    # 2. LE NOUVEL INPUT : Le contexte narratif (Le Pitch d'Ahmed Saad)
    candidate_narrative = """
    "Hi, I'm Ahmed. I am a PhD candidate specializing in the one thing that determines if an implant succeeds or fails: The Interface.
    In my research, I focused on modifying the surface of PEEK implants to make them actively bond with bone tissue, rather than just sitting there. I've spent years mastering the exact skills listed in your job description: surface chemistry, cell culture, and characterizing how new materials interact with the human body.
    I see that Medtronic is pushing the boundaries of what structural heart devices can do. You need materials that last longer and integrate better. Because I have a deep background in both the chemistry of the materials and the biology of the host response, I can help your R&D team solve biocompatibility issues before they become expensive failures in clinical trials.
    I'm looking to move from academic discovery to industrial application, and I'd love to bring my expertise in bioactive surfaces to your team."
    """

    # 3. L'Offre cible
    job_description_mock = "Principal Manufacturing/Process Engineer. Requires expertise in taking products from R&D to full-scale manufacturing. ISO 13485 required."

    print("📥 Données injectées : 3 Hard Skills Validés + Pitch Narratif du candidat.")
    print("--- ⚙️ LANCEMENT DU SCIENTIFIC SCORER ---")

    scorer = ScientificScorer()
    result = scorer.calculate_readiness_cot(
        tech_analysis=mock_tech_analysis, 
        job_description=job_description_mock,
        candidate_narrative=candidate_narrative
    )

    if result and "readiness_score" in result:
        print("\n" + "="*80)
        print(f"🎯 READINESS LEVEL GLOBAL : {result['readiness_score']} / 10.0")
        print("="*80)
        
        print(f"\n📝 RÉSUMÉ EXÉCUTIF (CTO) :\n{result.get('expert_summary')}")
        
        print("\n📊 DÉTAIL DES 3 DIMENSIONS :")
        for dim in ['transferability', 'pragmatism', 'complexity']:
            data = result.get(dim, {})
            print(f"\n🔹 {dim.upper()} : {data.get('score')}/5 - {data.get('label')}")
            print(f"   ↳ Argument  : {data.get('argument')}")
    else:
        print("\n💥 CRASH.")

if __name__ == "__main__":
    main()