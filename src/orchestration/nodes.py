import os
import json
import traceback
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

# Imports des schémas et de l'état
from src.schemas.state import MatchingState

# Imports des agents
from src.agents.job_parser import JobParserAgent
from src.memory.learning import KnowledgeExpander
from src.agents.hard_skills.bridge import BridgeAgent
from src.agents.hard_skills.auditor import CynicalAuditor
from src.agents.soft_skills.psycho import PsychometricAgent
from src.agents.soft_skills.rhetoric import RhetoricAgent
from src.agents.logistics.preference import PreferenceAgent
from src.agents.cv_quality.industry_cv_advisor import IndustryCVAdvisorAgent
from src.agents.career.role_recommender import RoleRecommenderAgent
from src.memory.graph_store import GraphStore
from src.scoring.global_scorer import GlobalScientificScorer

# ==========================================
# INITIALISATION DES SINGLETONS
# ==========================================
print("⚙️  Système : Initialisation des agents experts...")
job_parser = JobParserAgent()
expander = KnowledgeExpander()
bridge_agent = BridgeAgent()
auditor_agent = CynicalAuditor()
psy_agent = PsychometricAgent()
rhetoric_agent = RhetoricAgent()
pref_agent = PreferenceAgent()
cv_advisor_agent = IndustryCVAdvisorAgent()
role_recommender_agent = RoleRecommenderAgent()
global_scorer = GlobalScientificScorer()

def llm_retry_policy():
    return retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )

# ==========================================
# NŒUDS DE PRÉPARATION (SÉQUENTIELS)
# ==========================================

def node_initializer(state: MatchingState) -> MatchingState:
    """Analyse l'offre, extrait l'ADN et prépare le contexte."""
    print("\n [NODE: INITIALIZER]")
    try:
        cid = state.get("candidate_id", "")
        is_candidate_mode = (cid == "SELF_AUDIT_USER")
        job_desc = state['job_description'] 
        cv_text = state.get('raw_text_data', {}).get('cv', '')
        pitch_text = state.get('raw_text_data', {}).get('pitch', '')
        clarify_text = state.get('raw_text_data', {}).get('clarify', {})
        
        # 1. Extraction des métadonnées
        if is_candidate_mode:
            metadata = {"job_title": "Self-audit CV only", "contract_type": "N/A"}
            job_dna = {}
            print("    Mode candidat: extraction ADN poste bypassée.")
        else:
            metadata = job_parser.extract_metadata(job_desc)
            print(f"    Offre analysée : {metadata.get('job_title', 'Inconnu')}")

            # 2. SÉQUENÇAGE DE L'ADN (Le fix est ici !)
            print("    Séquençage de l'ADN du poste...")
            job_dna = bridge_agent.extract_job_dna(job_desc)

            # 3. APPRENTISSAGE CIBLÉ NEO4J (Le fix est ici !)
            skills_to_learn = job_dna.get("TOOL", []) + job_dna.get("STANDARD", [])
            if skills_to_learn:
                print(f"    Apprentissage Neo4j ciblé ({len(skills_to_learn)} concepts)...")
                try:
                    expander.learn_and_expand(skills_to_learn, job_desc[:4000]) 
                except Exception as e:
                    print(f"    Apprentissage ignoré (Erreur: {e})")
        
        return {
            "job_description": job_desc,
            "job_metadata": metadata,
            "job_dna": job_dna, # On sauvegarde l'ADN dans l'état !
            "managed_context": {"cv": cv_text, "pitch": pitch_text, "clarify": clarify_text},
            "retry_count": 0,
            "system_errors": []
        }
    except Exception as e:
        print(f"    Erreur Initializer : {e}")
        return {"system_errors": [f"Initializer: {str(e)}"]}

def node_bridge(state: MatchingState) -> MatchingState:
    print(f"\n [NODE: BRIDGE] (Essai {state.get('retry_count', 0)})")
    try:
        if state.get("candidate_id", "") == "SELF_AUDIT_USER":
            print("    Mode candidat: Bridge bypassé (pas d'ADN poste requis).")
            return {"tech_analysis": []}
        # On récupère l'ADN propre, pas le texte brut !
        job_dna = state.get('job_dna', {})
        
        @llm_retry_policy()
        def run():
            return bridge_agent.analyze(
                state['managed_context']['cv'], 
                job_dna, # On envoie le Dictionnaire d'ADN au Bridge !
                state.get('audit_feedback', '')
            )
        skills = run()
        print(f"    {len(skills)} compétences identifiées.")
        return {"tech_analysis": skills}
    except Exception as e:
        print(f"    Bridge en échec : {e}")
        return {"tech_analysis": [], "system_errors": state.get("system_errors", []) + ["Bridge Failed"]}

def node_auditor(state: MatchingState) -> MatchingState:
    print("\n⚖️  [NODE: CYNICAL AUDITOR]")
    if state.get("candidate_id", "") == "SELF_AUDIT_USER":
        print("    Mode candidat: Auditor bypassé.")
        return {
            "tech_analysis": state.get("tech_analysis", []),
            "last_verdict": "VALIDATED",
            "audit_feedback": "Bypass candidat CV-only.",
            "retry_count": 0,
        }
    skills = state.get('tech_analysis', [])
    if not skills:
        return {"last_verdict": "REJECTED", "audit_feedback": "Aucune compétence à auditer."}

    try:
        graph = GraphStore()
        domain_context = graph.get_definitions_context([s['skill_name'] for s in skills if s['status'] == 'FOUND'])
        graph.close()

        @llm_retry_policy()
        def run():
            return auditor_agent.audit(skills, state['managed_context']['cv'], domain_context)
        
        updated_skills, verdict, feedback = run()
        print(f"    Verdict : {verdict} | Skills validés : {len([s for s in updated_skills if s.get('confidence_score', 0) > 0.6])}")
        
        return {
            "tech_analysis": updated_skills,
            "last_verdict": verdict,
            "audit_feedback": feedback,
            "retry_count": state.get('retry_count', 0) + (1 if verdict == "REJECTED" else 0)
        }
    except Exception as e:
        print(f"    Audit Crash : {e}")
        safe_skills = state.get("tech_analysis", [])
        for skill in safe_skills:
            if skill.get("status") == "FOUND":
                skill["audit_status"] = "UNVERIFIED"
                skill["audit_comment"] = "Audit crash: validation impossible (fail-closed)."
        return {
            "tech_analysis": safe_skills,
            "last_verdict": "REJECTED",
            "audit_feedback": "Audit crash: impossible de confirmer les preuves.",
            "retry_count": state.get("retry_count", 0) + 1,
            "system_errors": state.get("system_errors", []) + ["Auditor Failed (Fail-Closed)"],
        }

# ==========================================
# NŒUDS PARALLÈLES (FAN-OUT)
# ==========================================

def node_psycho(state: MatchingState) -> MatchingState:
    print(" [PARALLEL] Psychometrics...")
    try:
        clarify = state.get("managed_context", {}).get("clarify", {})
        if isinstance(clarify, str):
            clarify = {"ikigai": clarify, "ideal_day": "", "smart_goals": ""}
            
        @llm_retry_policy()
        def run():
            return psy_agent.analyze_full_process({
                "pitch": state['managed_context']['pitch'],
                "ikigai": clarify.get("ikigai", ""),
                "ideal_day": clarify.get("ideal_day", ""),
                "smart_goals": clarify.get("smart_goals", "")
            }, state["job_description"])
        
        res = run()
        print("    Psycho Terminé.")
        return {"psychometrics": res}
    except Exception as e:
        print(f"    Psycho Error : {e}")
        return {"psychometrics": {"job_alignment_score": 0.0, "summary": "Erreur d'analyse."}}

def node_rhetoric(state: MatchingState) -> MatchingState:
    print("🎤 [PARALLEL] Rhetoric...")
    try:
        @llm_retry_policy()
        def run():
            return rhetoric_agent.analyze_pitch(state['managed_context']['pitch'])
        
        res = run()
        print("    Rhetoric Terminé.")
        return {"rhetoric_analysis": res}
    except Exception as e:
        print(f"    Rhetoric Error : {e}")
        return {"rhetoric_analysis": {"communication_score": 0.0, "feedback_summary": "Erreur API."}}

def node_logistics(state: MatchingState) -> MatchingState:
    print(" [PARALLEL] Logistics...")
    try:
        res = pref_agent.evaluate_feasibility(state.get('preferences_data', {}), state.get('job_metadata', {}))
        print("    Logistics Terminé.")
        return {"logistics_analysis": res}
    except Exception as e:
        print(f"    Logistics Error : {e}")
        return {"logistics_analysis": {"global_feasibility_score": 0.0}}

def node_cv_global(state: MatchingState) -> MatchingState:
    print(" [PARALLEL] CV Global Advisor...")
    try:
        managed = state.get("managed_context", {})
        candidate_mode = state.get("candidate_id", "") == "SELF_AUDIT_USER"
        res = cv_advisor_agent.analyze(
            cv_text=managed.get("cv", ""),
            pitch_text=managed.get("pitch", ""),
            job_description="" if candidate_mode else state.get("job_description", ""),
            tech_analysis=state.get("tech_analysis", []),
        )
        print("    CV Global Advisor Termine.")
        return {"cv_global_analysis": res}
    except Exception as e:
        print(f"    CV Global Error : {e}")
        return {
            "cv_global_analysis": {
                "profile_positioning": "ACADEMIC_BIASED",
                "confidence": 0.0,
                "industry_relevance": 0.0,
                "business_impact": 0.0,
                "transferability_narrative": 0.0,
                "brevity_focus": 0.0,
                "publication_calibration": 0.0,
                "evidence_quality": 0.0,
                "critical_risks": [],
                "priority_actions": [],
                "expert_summary": "Erreur d'analyse CV globale.",
                "overall_score": 0.0,
                "cv_style_flags": {},
            }
        }

def node_role_recommender(state: MatchingState) -> MatchingState:
    print(" [PARALLEL] Career Role Recommender...")
    try:
        managed = state.get("managed_context", {})
        res = role_recommender_agent.analyze(
            cv_text=managed.get("cv", ""),
            tech_analysis=state.get("tech_analysis", []),
            cv_global_analysis=state.get("cv_global_analysis", {}),
            preferences_data=state.get("preferences_data", {}),
        )
        print("    Role Recommender Termine.")
        return {"role_recommendations": res}
    except Exception as e:
        print(f"    Role Recommender Error : {e}")
        return {
            "role_recommendations": {
                "catalog_version": "unknown",
                "methodology": "evidence_constrained_deterministic_v1",
                "top_immediate_fit": [],
                "top_near_fit": [],
                "no_go_roles": [],
                "suggested_roles": [],
                "action_plan_30_60_90": {"30_days": [], "60_days": [], "90_days": []},
                "global_note": "Erreur d'analyse des postes recommandes."
            }
        }

# ==========================================
# CONVERGENCE ET SCORING FINAL
# ==========================================

def node_aggregator(state: MatchingState) -> MatchingState:
    print("\n [NODE: AGGREGATOR]")
    cid = state.get("candidate_id", "")
    missing = []
    is_candidate_mode = (cid == "SELF_AUDIT_USER")

    # 1. Vérification des branches
    if not is_candidate_mode:
        if not state.get("psychometrics"): missing.append("Psycho")
        if not state.get("rhetoric_analysis"): missing.append("Rhetoric")
        if not state.get("logistics_analysis"): missing.append("Logistics")
    if not state.get("cv_global_analysis"): missing.append("CV_Global")
    if is_candidate_mode and not state.get("role_recommendations"): missing.append("Role_Recommender")
    
    if missing:
        print(f"    Branches vides/manquantes détectées : {', '.join(missing)}.")

    # 2. ÉCRASEMENT DE SÉCURITÉ UNIVERSEL (Le Fix est ici)
    # On initialise TOUJOURS avec un dict vide par défaut pour éviter le crash du Scorer
    if not state.get("psychometrics"): state["psychometrics"] = {"job_alignment_score": 0.0}
    if not state.get("rhetoric_analysis"): state["rhetoric_analysis"] = {"communication_score": 0.0}
    if not state.get("logistics_analysis"): state["logistics_analysis"] = {"global_feasibility_score": 0.0}
    if not state.get("cv_global_analysis"): state["cv_global_analysis"] = {"overall_score": 0.0}
    if not state.get("role_recommendations"): state["role_recommendations"] = {"top_immediate_fit": [], "top_near_fit": [], "no_go_roles": [], "suggested_roles": []}

    print(" Fusion des données terminée.")
    return state

def node_final_scoring(state: MatchingState) -> MatchingState:
    print("\n [NODE: FINAL SCORING]")
    try:
        final_input = {
            "candidate_id": state.get("candidate_id", "Unknown"),
            "job_description": state.get("job_description", ""),
            "raw_text_data": state.get("raw_text_data", {}),
            "tech_analysis": state.get("tech_analysis", []),
            "psychometrics": state.get("psychometrics", {}),
            "rhetoric_analysis": state.get("rhetoric_analysis", {}),
            "logistics_analysis": state.get("logistics_analysis", {}),
            "cv_global_analysis": state.get("cv_global_analysis", {}),
            "role_recommendations": state.get("role_recommendations", {}),
            "system_errors": state.get("system_errors", [])
        }
        
        report = global_scorer.finalize_matching_report(final_input)
        print(f"    SCORE FINAL : {report.get('score_out_of_10', 0)}/10")
        return {
            "readiness_diagnostic": report,
            "final_readiness_score": report.get("score_out_of_10", 0.0)
        }
    except Exception as e:
        print(f"    CRASH SCORER FINAL : {e}")
        traceback.print_exc()
        return {"final_readiness_score": 0.0}
