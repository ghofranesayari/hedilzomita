from typing import Dict

from src.scoring.scientific_scorer import ScientificScorer


class GlobalScientificScorer:
    INTERNAL_WEIGHTS = {
        "tech": 0.45,
        "psycho": 0.18,
        "comm": 0.12,
        "log": 0.10,
        "cv": 0.15,
    }
    CANDIDATE_WEIGHTS = {
        "tech": 0.75,
        "cv": 0.25,
    }

    def __init__(self):
        self.scientific_scorer = ScientificScorer()

    def finalize_matching_report(self, state: Dict) -> Dict:
        print("Global Scorer: Synthese de tous les axes paralleles...")

        raw_data = state.get("raw_text_data", {})
        pitch = raw_data.get("pitch", "")
        clarify = raw_data.get("clarify", {})
        ikigai = clarify.get("ikigai", "") if isinstance(clarify, dict) else ""
        candidate_narrative = f"{pitch}\n{ikigai}"

        tech_diag = self.scientific_scorer.calculate_readiness_cot(
            tech_analysis=state.get("tech_analysis", []),
            job_description=state.get("job_description", ""),
            candidate_narrative=candidate_narrative,
        )

        rhetoric_data = state.get("rhetoric_analysis", {})
        comm_score = float(rhetoric_data.get("communication_score", 0.0))

        logistics_data = state.get("logistics_analysis", {})
        log_score = float(logistics_data.get("global_feasibility_score", 0.0))

        psycho_data = state.get("psychometrics", {})
        psycho_score = float(psycho_data.get("job_alignment_score", 0.0))

        cv_data = state.get("cv_global_analysis", {})
        cv_score = float(cv_data.get("overall_score", 0.0))
        career_data = state.get("role_recommendations", {})

        tech_global_score = float(tech_diag.get("readiness_score", 0.0))

        is_candidate_mode = (
            state.get("candidate_id", "") == "SELF_AUDIT_USER"
            or str(state.get("execution_mode", "")).strip().lower() == "candidate"
        )

        if is_candidate_mode:
            # Candidate mode runs only CV + career logic; avoid penalizing non-executed axes.
            final_10 = (
                (tech_global_score * self.CANDIDATE_WEIGHTS["tech"])
                + (cv_score * self.CANDIDATE_WEIGHTS["cv"])
            )
            dimensions = {
                "Readiness scientifique (75%)": tech_global_score,
                "Qualite CV industrie (25%)": cv_score,
            }
            scoring_mode = "candidate_cv_only"
            scoring_weights = self.CANDIDATE_WEIGHTS
        else:
            # Internal mode full stack: keep original weighting.
            final_10 = (
                (tech_global_score * self.INTERNAL_WEIGHTS["tech"])
                + (psycho_score * self.INTERNAL_WEIGHTS["psycho"])
                + (comm_score * self.INTERNAL_WEIGHTS["comm"])
                + (log_score * self.INTERNAL_WEIGHTS["log"])
                + (cv_score * self.INTERNAL_WEIGHTS["cv"])
            )
            dimensions = {
                "Readiness scientifique (45%)": tech_global_score,
                "Fit Psychometrique (18%)": psycho_score,
                "Communication (12%)": comm_score,
                "Faisabilite (10%)": log_score,
                "Qualite CV industrie (15%)": cv_score,
            }
            scoring_mode = "internal_full"
            scoring_weights = self.INTERNAL_WEIGHTS

        return {
            "candidate_id": state.get("candidate_id", "UNKNOWN"),
            "readiness_level": round((final_10 / 10) * 9, 1),
            "score_out_of_10": round(final_10, 1),
            "dimensions": dimensions,
            "scoring_mode": scoring_mode,
            "scoring_weights": scoring_weights,
            "tech_details": tech_diag,
            "cv_details": cv_data,
            "career_details": career_data,
            "expert_verdict": tech_diag.get(
                "expert_summary", "Evaluation technique non generee."
            ),
            "cv_expert_summary": cv_data.get(
                "expert_summary", "Evaluation CV globale non generee."
            ),
        }
