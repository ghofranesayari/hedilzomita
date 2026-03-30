import os
import json
from pathlib import Path
from src.ingestion.parser import ContentParser
from src.agents.hard_skills.bridge import BridgeAgent
from src.agents.hard_skills.auditor import CynicalAuditor
from src.memory.learning import KnowledgeExpander
from src.memory.graph_store import GraphStore

def load_specific_job(filename: str) -> str:
    job_dir = Path("data/raw_jobs")
    if not job_dir.exists(): job_dir = Path("data/rawjobs")
    target_path = job_dir / filename
    if not target_path.exists(): raise FileNotFoundError(f"❌ L'offre '{filename}' est introuvable.")
    print(f" Offre chargée : {target_path.name}")
    return ContentParser().parse_pdf(target_path)

def load_specific_candidate(candidate_id: str) -> dict:
    proc_dir = Path("data/processed")
    for file in proc_dir.iterdir():
        if file.suffix == '.json' and candidate_id in file.name:
            print(f"👤 Candidat chargé : {file.name}")
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
    raise FileNotFoundError(f" Le candidat '{candidate_id}' est introuvable.")

def main():
    print("="*70)
    print(" ISOLATION TEST STRICT : PHASE 3 (BRIDGE -> LEARNING -> SEARCH -> AUDIT)")
    print("="*70)

    # 🎯 PARAMÉTRAGE
    NOM_DU_FICHIER_OFFRE = "LambdaVision_Biomedical_Engineer_II_Job_Description_2021.pdf" 
    ID_DU_CANDIDAT = "CANDIDATE_2E4A2750" 

    # 1. Chargement des données
    try:
        job_text = load_specific_job(NOM_DU_FICHIER_OFFRE)
        cand_data = load_specific_candidate(ID_DU_CANDIDAT)
    except FileNotFoundError as e:
        print(e); return
    cv_text = cand_data.get("cv_text", "")

    print("\n🔌 Connexion au Graphe Neo4j...")
    graph = GraphStore()
    
    # 🚨🚨 TRES IMPORTANT : ON VIDE LA BASE POUR LE TEST 🚨🚨
    print("🧹 Nettoyage de Neo4j (Suppression des vieilles hallucinations)...")
    with graph.driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    expander = KnowledgeExpander()
    bridge = BridgeAgent()
    auditor = CynicalAuditor()

    # --- LE NOUVEL ORDRE LOGIQUE ---

     # ETAPE 1 : Le Bridge lit l'offre et séquence l'ADN complet
    print("\n--- 🧬 1. BRIDGE : SÉQUENÇAGE DE L'ADN DU POSTE ---")
    job_dna = bridge.extract_job_dna(job_text)
    print(json.dumps(job_dna, indent=2, ensure_ascii=False))

    # ETAPE 2 : Le Cerveau apprend UNIQUEMENT les Outils et Normes
    # On ne pollue pas Neo4j avec les descriptions de responsabilités ou diplômes !
    print("\n--- 🧠 2. KNOWLEDGE EXPANDER : APPRENTISSAGE CIBLÉ ---")
    skills_to_learn = job_dna.get("TOOL", []) + job_dna.get("STANDARD", [])
    if skills_to_learn:
        expander.learn_and_expand(skills_to_learn, job_text)
    else:
        print("Aucun outil ou norme technique à apprendre.")

    # ETAPE 3 : Le Bridge cherche dans le CV
    print("\n--- 🌉 3. BRIDGE : FOUILLE MULTIDIMENSIONNELLE ---")
    skills = bridge.analyze(cv_text, job_dna)
    print("\n[Résultat Brut du Bridge] :")
    print(json.dumps(skills, indent=2, ensure_ascii=False))

    # ETAPE 4 : L'Auditeur vérifie
    print("\n--- ⚖️ 4. CYNICAL AUDITOR : VÉRIFICATION FINALE ---")
    skill_names = [s['skill_name'] for s in skills if s['status'] in ['FOUND', 'INFERRED']]
    real_domain_context = graph.get_definitions_context(skill_names)
    
    audited_skills, verdict, feedback = auditor.audit(skills, cv_text, real_domain_context)
    
    print("\n📊 RÉSULTAT FINAL DE L'AUDIT :")
    print(f"VERDICT GLOBAL : {verdict}")
    print(f"FEEDBACK : {feedback}")
    print("\nDÉTAIL DES COMPÉTENCES VALIDÉES/REJETÉES :")
    print(json.dumps(audited_skills, indent=2, ensure_ascii=False))
    
    graph.close()

if __name__ == "__main__":
    main()