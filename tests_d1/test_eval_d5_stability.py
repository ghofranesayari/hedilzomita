from scripts.eval_d3_stability import _evaluate_stability_gate, _series_stats


def test_series_stats_basic():
    stats = _series_stats([0.8, 0.8, 0.8])
    assert stats["mean"] == 0.8
    assert stats["std"] == 0.0
    assert stats["min"] == 0.8
    assert stats["max"] == 0.8


def test_stability_gate_pass():
    summary = {
        "micro_f1": {"std": 0.005},
        "unsupported_evidence_rate": {"std": 0.01},
        "false_claim_acceptance_rate": {"std": 0.01},
    }
    gate = _evaluate_stability_gate(summary, 0.02, 0.02, 0.02)
    assert gate["status"] == "PASS"


def test_stability_gate_fail():
    summary = {
        "micro_f1": {"std": 0.03},
        "unsupported_evidence_rate": {"std": 0.01},
        "false_claim_acceptance_rate": {"std": 0.01},
    }
    gate = _evaluate_stability_gate(summary, 0.02, 0.02, 0.02)
    assert gate["status"] == "FAIL"
