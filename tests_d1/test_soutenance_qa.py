from scripts.build_soutenance_qa import _build_qa_markdown


def test_build_qa_contains_core_sections():
    md = _build_qa_markdown(d3={}, d5={}, d6={})
    assert "# Q&A Jury - Soutenance" in md
    assert "Questions et reponses pretes" in md
    assert "Q1." in md


def test_build_qa_injects_metrics_values():
    d3 = {
        "summary": {
            "micro_f1": 0.9,
            "unsupported_evidence_rate": 0.2,
            "false_claim_acceptance_rate": 0.1,
        }
    }
    d5 = {"stability_gate": {"status": "PASS"}}
    d6 = {"readiness_gate": {"status": "PASS"}}
    md = _build_qa_markdown(d3=d3, d5=d5, d6=d6)
    assert "0.9" in md
    assert "status=PASS" in md
