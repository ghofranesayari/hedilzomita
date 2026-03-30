import json
from pathlib import Path

from scripts.build_release_readiness import _build_payload


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_release_readiness_pass_when_all_gates_and_artifacts_present(tmp_path: Path):
    _write_json(tmp_path / "outputs/evaluation/d3/metrics_d3.json", {"gate": {"status": "PASS"}})
    _write_json(tmp_path / "outputs/evaluation/d3/stability_d5.json", {"stability_gate": {"status": "PASS"}})
    _write_json(tmp_path / "outputs/evaluation/d3/calibration_d6.json", {"readiness_gate": {"status": "PASS"}})
    _write_json(tmp_path / "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json", {"global_status": "PASS"})

    required = [
        "outputs/soutenance/SOUTENANCE_1PAGE.md",
        "outputs/soutenance/SOUTENANCE_DETAILLEE.md",
        "outputs/soutenance/DRY_RUN_SOUTENANCE.md",
        "outputs/soutenance/QA_JURY.md",
        "outputs/soutenance/AEBM_HANDOVER_PACKAGE.zip",
        "outputs/soutenance/HANDOVER_BUNDLE_MANIFEST.json",
    ]
    for rel in required:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("ok", encoding="utf-8")

    payload = _build_payload(tmp_path)
    assert payload["overall_status"] == "PASS"


def test_release_readiness_fail_if_missing_artifact(tmp_path: Path):
    _write_json(tmp_path / "outputs/evaluation/d3/metrics_d3.json", {"gate": {"status": "PASS"}})
    _write_json(tmp_path / "outputs/evaluation/d3/stability_d5.json", {"stability_gate": {"status": "PASS"}})
    _write_json(tmp_path / "outputs/evaluation/d3/calibration_d6.json", {"readiness_gate": {"status": "PASS"}})
    _write_json(tmp_path / "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json", {"global_status": "PASS"})

    payload = _build_payload(tmp_path)
    assert payload["overall_status"] == "FAIL"
    assert payload["gates"]["artifact_presence"] == "FAIL"
