import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from src.agents.soft_skills.rhetoric import RhetoricAgent

def load_specific_candidate(candidate_id: str) -> dict:
    proc_dir = Path("data/processed")
    for file in proc_dir.iterdir():
        if file.suffix == '.json' and candidate_id in file.name:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
    raise FileNotFoundError(f"❌ Le candidat '{candidate_id}' est introuvable.")

def main():
    print("="*80)
    print("🗣️ ISOLATION TEST STRICT : PHASE 4B (AGENT RHÉTORIQUE V2)")
    print("="*80)

    ID_DU_CANDIDAT = "CANDIDATE_08D63E65" # Hao-Han
    try:
        cand_data = load_specific_candidate(ID_DU_CANDIDAT)
    except Exception as e:
        print(e); return

    pitch_text = cand_data.get("pitch_text", "")
    print(f"\n🔍 Pitch analysé : {len(pitch_text)} caractères.")
    
    agent = RhetoricAgent()
    result = agent.analyze_pitch(pitch_text)

    if result:
        print("\n" + "="*80)
        print(f"⭐ SCORE FINAL DE COMMUNICATION : {result['communication_score']} / 10")
        print(f"🧠 Score d'Agentivité (Bandura)  : {result['tonal_analysis']['agency_score']} / 1.0")
        print(f"📖 Clarté Opérationnelle        : {result['tonal_analysis']['clarity_score']} / 1.0")
        print("="*80)
        
        print("\n🎯 CONSEILS DE RÉÉCRITURE (NO-BULLSHIT) :")
        for i, advice in enumerate(result.get('improvement_advice', []), 1):
            print(f"  {i}. {advice}")
            
        print("\n📉 DÉTAIL DU JSON :")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n💥 CRASH TOTAL.")

if __name__ == "__main__":
    main()