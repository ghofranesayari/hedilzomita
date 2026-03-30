from src.scoring.global_scorer import GlobalScientificScorer


class _DummyScientificScorer:
    def calculate_readiness_cot(self, **kwargs):
        return {"readiness_score": 6.0, "expert_summary": "ok"}


def _build_scorer():
    scorer = GlobalScientificScorer.__new__(GlobalScientificScorer)
    scorer.scientific_scorer = _DummyScientificScorer()
    return scorer


def test_candidate_mode_uses_only_cv_and_tech_axes():
    scorer = _build_scorer()
    state = {
        "candidate_id": "SELF_AUDIT_USER",
        "execution_mode": "candidate",
        "cv_global_analysis": {"overall_score": 8.0},
        "rhetoric_analysis": {"communication_score": 1.0},
        "logistics_analysis": {"global_feasibility_score": 1.0},
        "psychometrics": {"job_alignment_score": 1.0},
    }
    out = scorer.finalize_matching_report(state)

    assert out["scoring_mode"] == "candidate_cv_only"
    assert len(out["dimensions"]) == 2
    assert out["score_out_of_10"] == 6.5  # 6.0*0.75 + 8.0*0.25


def test_internal_mode_keeps_full_weighting():
    scorer = _build_scorer()
    state = {
        "candidate_id": "CAND_001",
        "execution_mode": "internal",
        "cv_global_analysis": {"overall_score": 8.0},
        "rhetoric_analysis": {"communication_score": 7.0},
        "logistics_analysis": {"global_feasibility_score": 5.0},
        "psychometrics": {"job_alignment_score": 6.0},
    }
    out = scorer.finalize_matching_report(state)

    assert out["scoring_mode"] == "internal_full"
    assert len(out["dimensions"]) == 5
    assert abs(out["score_out_of_10"] - 6.3) < 1e-9
