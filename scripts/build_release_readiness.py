import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _load_json_optional(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _status(v: Any) -> str:
    return str(v or "UNKNOWN").upper()


def _build_payload(project_root: Path) -> Dict[str, Any]:
    d3 = _load_json_optional(project_root / "outputs/evaluation/d3/metrics_d3.json")
    d5 = _load_json_optional(project_root / "outputs/evaluation/d3/stability_d5.json")
    d6 = _load_json_optional(project_root / "outputs/evaluation/d3/calibration_d6.json")
    checklist = _load_json_optional(project_root / "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json")

    required_files = [
        "outputs/soutenance/SOUTENANCE_1PAGE.md",
        "outputs/soutenance/SOUTENANCE_DETAILLEE.md",
        "outputs/soutenance/DRY_RUN_SOUTENANCE.md",
        "outputs/soutenance/QA_JURY.md",
        "outputs/soutenance/AEBM_HANDOVER_PACKAGE.zip",
        "outputs/soutenance/HANDOVER_BUNDLE_MANIFEST.json",
    ]
    files = []
    for rel in required_files:
        exists = (project_root / rel).exists()
        files.append({"path": rel, "exists": exists})

    d3_status = _status(d3.get("gate", {}).get("status"))
    d5_status = _status(d5.get("stability_gate", {}).get("status"))
    d6_status = _status(d6.get("readiness_gate", {}).get("status"))
    checklist_status = _status(checklist.get("global_status"))
    files_status = "PASS" if all(f["exists"] for f in files) else "FAIL"

    gates = {
        "d3_gate": d3_status,
        "d5_gate": d5_status,
        "d6_gate": d6_status,
        "pre_soutenance_checklist": checklist_status,
        "artifact_presence": files_status,
    }
    overall = "PASS" if all(v == "PASS" for v in gates.values()) else "FAIL"

    return {
        "protocol_version": "e6_release_readiness_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "overall_status": overall,
        "gates": gates,
        "required_artifacts": files,
    }


def _build_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Release Readiness")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{payload.get('generated_at_utc', 'n/a')}`")
    lines.append(f"- Overall status: `{payload.get('overall_status', 'UNKNOWN')}`")
    lines.append("")
    lines.append("## Gates")
    lines.append("")
    for key, value in payload.get("gates", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Required Artifacts")
    lines.append("")
    for item in payload.get("required_artifacts", []):
        mark = "OK" if item.get("exists") else "MISSING"
        lines.append(f"- [{mark}] `{item.get('path')}`")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final release readiness report")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-json", default="outputs/soutenance/RELEASE_READINESS.json")
    parser.add_argument("--output-md", default="outputs/soutenance/RELEASE_READINESS.md")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    payload = _build_payload(project_root)

    out_json = (project_root / args.output_json).resolve()
    out_md = (project_root / args.output_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_build_markdown(payload), encoding="utf-8")

    print(f"[E6] JSON: {out_json}")
    print(f"[E6] MD  : {out_md}")
    print(f"[E6] OVERALL: {payload['overall_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
