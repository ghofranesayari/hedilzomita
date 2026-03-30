from scripts.eval_d3 import _evaluate_gate, _prf1, evaluate_d3


def test_prf1_basic_case():
    p, r, f1 = _prf1(tp=8, fp=2, fn=2)
    assert round(p, 4) == 0.8
    assert round(r, 4) == 0.8
    assert round(f1, 4) == 0.8


def test_prf1_zero_division_case():
    p, r, f1 = _prf1(tp=0, fp=0, fn=0)
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


def test_evaluate_d3_perfect_prediction():
    golden = [
        {
            "sample_id": "CV_001",
            "cv_text": "Built python pipeline and validation workflow.",
            "ground_truth": {
                "hard_skills_present": ["python", "validation"],
                "hard_skills_absent": ["aws"],
            },
        }
    ]
    predictions = [
        {
            "sample_id": "CV_001",
            "predicted_hard_skills": ["python", "validation"],
            "evidence_items": [
                {"skill": "python", "snippet": "python pipeline", "supported": True},
                {"skill": "validation", "snippet": "validation workflow", "supported": True},
            ],
        }
    ]

    metrics = evaluate_d3(golden, predictions)
    summary = metrics["summary"]
    counters = metrics["counters"]

    assert summary["micro_f1"] == 1.0
    assert summary["unsupported_evidence_rate"] == 0.0
    assert summary["false_claim_acceptance_rate"] == 0.0
    assert counters["tp"] == 2
    assert counters["fp"] == 0
    assert counters["fn"] == 0


def test_evaluate_d3_no_prediction_coverage_zero():
    golden = [
        {
            "sample_id": "CV_002",
            "cv_text": "Cell culture and CRISPR work.",
            "ground_truth": {
                "hard_skills_present": ["cell culture", "crispr"],
                "hard_skills_absent": ["fda submission"],
            },
        }
    ]

    metrics = evaluate_d3(golden, prediction_rows=[])
    summary = metrics["summary"]

    assert summary["samples_total"] == 1
    assert summary["samples_with_prediction"] == 0
    assert summary["coverage_rate"] == 0.0
    assert summary["micro_precision"] == 0.0
    assert summary["micro_recall"] == 0.0
    assert summary["micro_f1"] == 0.0


def test_evaluate_d3_evidence_fallback_and_false_claim_rate():
    golden = [
        {
            "sample_id": "CV_003",
            "cv_text": "Postdoctoral researcher in protein engineering.",
            "ground_truth": {
                "hard_skills_present": ["protein engineering"],
                "hard_skills_absent": ["fda submission", "gmp"],
            },
        }
    ]
    predictions = [
        {
            "sample_id": "CV_003",
            "predicted_hard_skills": ["protein engineering", "fda submission"],
            # no explicit 'supported' flag, snippet-based fallback should apply
            "evidence_items": [
                {"skill": "protein engineering", "snippet": "protein engineering"},
                {"skill": "fda submission", "snippet": "prepared fda submission"},
            ],
        }
    ]

    metrics = evaluate_d3(golden, predictions)
    summary = metrics["summary"]
    counters = metrics["counters"]

    # TP=1, FP=1, FN=0 -> micro precision=0.5, recall=1.0, f1=0.6667
    assert summary["micro_precision"] == 0.5
    assert summary["micro_recall"] == 1.0
    assert summary["micro_f1"] == 0.6667

    # 1 unsupported evidence over 2 items
    assert summary["unsupported_evidence_rate"] == 0.5
    assert counters["unsupported_evidence"] == 1
    assert counters["total_evidence"] == 2

    # 1 false accepted absent skill over 2 absent labels
    assert summary["false_claim_acceptance_rate"] == 0.5
    assert counters["false_accept_absent"] == 1
    assert counters["total_absent_labels"] == 2


def test_gate_pass_and_fail():
    base_metrics = {
        "summary": {
            "micro_f1": 0.70,
        }
    }
    gate_pass = _evaluate_gate(base_metrics, min_micro_f1=0.65)
    assert gate_pass["status"] == "PASS"

    gate_fail = _evaluate_gate(base_metrics, min_micro_f1=0.75)
    assert gate_fail["status"] == "FAIL"
