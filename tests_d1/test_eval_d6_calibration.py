from scripts.eval_d6_calibration import _evaluate_readiness, _recommend_thresholds


def test_recommend_thresholds_shape():
    d3 = {
        "summary": {
            "micro_f1": 0.8,
            "unsupported_evidence_rate": 0.2,
            "false_claim_acceptance_rate": 0.3,
        }
    }
    d5 = {"aggregate": {"micro_f1": {"std": 0.01}}}
    out = _recommend_thresholds(d3, d5)
    assert "min_micro_f1" in out
    assert "max_unsupported_evidence_rate" in out
    assert "max_false_claim_acceptance_rate" in out
    assert "max_stability_std_micro_f1" in out


def test_evaluate_readiness_pass():
    d3 = {
        "summary": {
            "micro_f1": 0.85,
            "unsupported_evidence_rate": 0.2,
            "false_claim_acceptance_rate": 0.3,
        }
    }
    d4 = {"variants": [{"variant": "baseline", "gate_status": "PASS"}, {"variant": "noisy", "gate_status": "FAIL"}]}
    d5 = {"aggregate": {"micro_f1": {"std": 0.0}}}
    thresholds = {
        "min_micro_f1": 0.8,
        "max_unsupported_evidence_rate": 0.25,
        "max_false_claim_acceptance_rate": 0.35,
        "max_stability_std_micro_f1": 0.02,
    }
    result = _evaluate_readiness(d3, d4, d5, thresholds)
    assert result["status"] == "PASS"


def test_evaluate_readiness_fail_when_no_fail_variant():
    d3 = {
        "summary": {
            "micro_f1": 0.85,
            "unsupported_evidence_rate": 0.2,
            "false_claim_acceptance_rate": 0.3,
        }
    }
    d4 = {"variants": [{"variant": "baseline", "gate_status": "PASS"}]}
    d5 = {"aggregate": {"micro_f1": {"std": 0.0}}}
    thresholds = {
        "min_micro_f1": 0.8,
        "max_unsupported_evidence_rate": 0.25,
        "max_false_claim_acceptance_rate": 0.35,
        "max_stability_std_micro_f1": 0.02,
    }
    result = _evaluate_readiness(d3, d4, d5, thresholds)
    assert result["status"] == "FAIL"
