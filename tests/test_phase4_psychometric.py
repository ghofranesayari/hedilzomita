import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.ingestion.parser import ContentParser
from src.agents.soft_skills.psycho import PsychometricAgent

def load_specific_job(filename: str) -> str:
    job_dir = Path("data/raw_jobs")
    if not job_dir.exists():
        job_dir = Path("data/rawjobs")
        
    target_path = job_dir / filename
    if not target_path.exists():
        raise FileNotFoundError(f"❌ L'offre '{filename}' est introuvable dans {job_dir}.")
    
    print(f"📄 Offre chargée : {target_path.name}")
    try:
        return ContentParser().parse_pdf(target_path)
    except Exception as e:
        print(f"⚠️ Erreur OCR ({e}). Utilisation d'un texte de secours.")
        return "Job Requirements: R&D environment, fast-paced startup, requires cross-functional leadership, ISO 13485, SolidWorks."

def load_specific_candidate(candidate_id: str) -> dict:
    proc_dir = Path("data/processed")
    for file in proc_dir.iterdir():
        if file.suffix == '.json' and candidate_id in file.name:
            print(f"👤 Candidat chargé : {file.name}")
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
    raise FileNotFoundError(f"❌ Le candidat '{candidate_id}' est introuvable dans {proc_dir}.")

def main():
    print("="*70)
    print("🧠 ISOLATION TEST STRICT : PHASE 4 (AGENT PSYCHOMÉTRIQUE)")
    print("="*70)

    # 🎯 PARAMÉTRAGE FIXE POUR HAO-HAN
    NOM_DU_FICHIER_OFFRE = "Principal-Manufacturing-Process-Engineer_8.27.2020.pdf" 
    ID_DU_CANDIDAT = "CANDIDATE_08D63E65" # Hao-Han

    # 1. Chargement
    try:
        job_text = load_specific_job(NOM_DU_FICHIER_OFFRE)
        cand_data = load_specific_candidate(ID_DU_CANDIDAT)
    except FileNotFoundError as e:
        print(e)
        return

    # 2. Formatage
    clarify = cand_data.get("clarify_text", {})
    raw_data = {
        "pitch": cand_data.get("pitch_text", ""),
        "ikigai": clarify.get("ikigai", ""),
        "smart_goals": clarify.get("smart_goals", ""),
        "ideal_day": clarify.get("ideal_day", "")
    }

    # 3. Exécution
    print("\n--- 🧠 LANCEMENT DU PSYCHOMETRIC AGENT ---")
    psycho_agent = PsychometricAgent()
    result = psycho_agent.analyze_full_process(raw_data, job_text)

    # 4. Affichage (Sans graphique pour éviter les plantages)
    if result:
        print("\n" + "="*70)
        print("📊 RÉSULTAT DE L'ANALYSE PSYCHOMÉTRIQUE :")
        print(f"⭐ SCORE D'ALIGNEMENT GLOBAL : {result.get('job_alignment_score', 0.0)} / 10")
        
        # --- AFFICHAGE DU BREAKDOWN (TICKET DE CAISSE) ---
        if "scoring_breakdown" in result:
            print("\n🧾 DÉTAIL DU CALCUL (TICKET DE CAISSE) :")
            bd = result["scoring_breakdown"]
            print(f"  • Base (Cosinus)         : {bd.get('base_match_cosine')} / 10")
            print(f"  • Pénalité de distance   : -{bd.get('total_distance_penalty')} pts")
            print(f"  • Plus grand écart       : {bd.get('biggest_gap_detected')}")
            
            if bd.get('cognitive_dissonance_flag'):
                print(f"  • ⚠️ MALUS DISSONANCE COGNITIVE : -{bd.get('cognitive_dissonance_penalty')} pts")
        
        print("="*70)
        print("\n📉 DÉTAIL DU JSON :")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n💥 CRASH TOTAL.")

if __name__ == "__main__":
    main()