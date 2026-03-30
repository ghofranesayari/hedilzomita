import os
from dotenv import load_dotenv
from src.agents.soft_skills.rhetoric import RhetoricAgent

load_dotenv()

def run_rhetoric_audit():
    agent = RhetoricAgent()

    print("🔬 === LABORATOIRE D'AUDIT : AGENT DE RHÉTORIQUE (S.T.A.R) === 🔬\n")

    # =========================================================================
    # TEST 1 : LA BASELINE PARFAITE (Équilibré et chiffré)
    # =========================================================================
    print("⏳ Test 1 : Le Pitch Parfait (Baseline)...")
    pitch_baseline = """
    Hi, I'm Ahmed. During my PhD, my lab faced a major bottleneck: evaluating implant biocompatibility took 3 weeks per batch. 
    I took the initiative to redesign the testing protocol. I developed an automated screening assay using ImageJ and Python. 
    As a result, I reduced the processing time by 40% and saved the lab approximately $5,000 in reagent costs per semester. 
    I am looking to bring this efficiency to your R&D team.
    """
    res_base = agent.analyze_pitch(pitch_baseline)
    print(f"📊 Score Global : {res_base['communication_score']}/10")
    print(f"🎯 Action: {res_base['star_breakdown']['Action']['quality']} | Résultat: {res_base['star_breakdown']['Result']['quality']}\n")

    # =========================================================================
    # TEST 2 : LE "BEAU PARLEUR" (Beaucoup de style, zéro chiffre)
    # But : Voir si l'IA applique bien la pénalité sur l'absence de métrique.
    # =========================================================================
    print("⏳ Test 2 : Le Biais du 'Beau Parleur' (Style over Substance)...")
    pitch_storyteller = """
    Hello! I am a highly motivated and deeply passionate visionary. I was faced with an incredibly difficult project where everything was going wrong. 
    However, I stepped up as a true leader. I completely transformed our approach, worked day and night, and completely revolutionized the way the team operated. 
    Thanks to my hard work, the project was a massive success, the client was extremely happy, and everyone congratulated me. I am a true game-changer!
    """
    res_story = agent.analyze_pitch(pitch_storyteller)
    print(f"📊 Score Global : {res_story['communication_score']}/10 (Attendu: Faible malgré l'enthousiasme)")
    print(f"🎯 Résultat (R) : {res_story['star_breakdown']['Result']['quality']}")
    print(f"💡 Raisonnement R : {res_story['star_breakdown']['Result']['reasoning']}\n")

    # =========================================================================
    # TEST 3 : LE SYNDROME DE L'IMPOSTEUR (Le "Nous" modeste)
    # But : Tester si l'IA détecte la voix passive et l'absence de leadership direct.
    # =========================================================================
    print("⏳ Test 3 : Le Modeste / Voix Passive (Biais d'Agentivité)...")
    pitch_humble = """
    Hello. During my time at the university, there was a project about materials. 
    I was part of a team that was assigned to solve a problem with cell culture. 
    We worked together, and I was given the task of preparing the samples. 
    It was a great team effort, and a paper was eventually published by our laboratory which showed a 20% improvement in cell viability.
    """
    res_humble = agent.analyze_pitch(pitch_humble)
    print(f"📊 Score Global : {res_humble['communication_score']}/10")
    print(f"🎯 Voix Dominante : {res_humble['tonal_analysis']['voice_type']} (Attendu: PASSIVE/MIXED)")
    print(f"🎯 Action (A) : {res_humble['star_breakdown']['Action']['quality']} (Attendu: Faible car le candidat s'efface)\n")

    # =========================================================================
    # TEST 4 : LE JARGON BOMBER (Complexité inutile)
    # But : Vérifier la pénalité de lisibilité (Clarity).
    # =========================================================================
    print("⏳ Test 4 : Le Jargon Bomber (Analyse de Lisibilité)...")
    pitch_jargon = """
    I systematically leveraged synergistic cross-platform paradigms to incentivize holistic bandwidth. 
    By orchestrating scalable infomediaries and granular ROI methodologies, I was able to disintermediate 
    the bleeding-edge supply chains, resulting in a paradigm shift that boosted our core synergistic deliverables by 15.3%.
    """
    res_jargon = agent.analyze_pitch(pitch_jargon)
    print(f"📊 Score Global : {res_jargon['communication_score']}/10")
    print(f"📉 Score de Clarté : {res_jargon['tonal_analysis']['clarity_score']}/10 (Attendu: Très bas)")
    print(f"💡 Retour du Coach : {res_jargon['feedback_summary']}\n")


if __name__ == "__main__":
    run_rhetoric_audit()