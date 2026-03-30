import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _exists(path: Path) -> bool:
    return path.exists()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_required_files(project_root: Path) -> List[Tuple[str, bool, str]]:
    required = [
        ("App entrypoint", project_root / "app.py"),
        ("Launcher", project_root / "Demarrer_The_Sovereign.bat"),
        ("Guide utilisateur", project_root / "Guide_Utilisation.md"),
        ("D3 metrics", project_root / "outputs" / "evaluation" / "d3" / "metrics_d3.json"),
        ("D4 ablation", project_root / "outputs" / "evaluation" / "d3" / "ablation_d4.json"),
        ("D5 stability", project_root / "outputs" / "evaluation" / "d3" / "stability_d5.json"),
        ("D6 calibration", project_root / "outputs" / "evaluation" / "d3" / "calibration_d6.json"),
        ("Soutenance 1-page", project_root / "outputs" / "soutenance" / "SOUTENANCE_1PAGE.md"),
        ("Soutenance detaillee", project_root / "outputs" / "soutenance" / "SOUTENANCE_DETAILLEE.md"),
    ]
    results = []
    for label, path in required:
        ok = _exists(path)
        results.append((label, ok, path.as_posix()))
    return results


def _check_env(project_root: Path) -> List[Tuple[str, bool, str]]:
    env_path = project_root / ".env"
    out: List[Tuple[str, bool, str]] = []
    if not env_path.exists():
        out.append(("Env file .env", False, ".env missing"))
        return out

    raw = env_path.read_text(encoding="utf-8", errors="ignore")
    required_vars = ["GROQ_API_KEY", "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]
    for var in required_vars:
        present = any(line.startswith(f"{var}=") for line in raw.splitlines())
        out.append((f"Env var {var}", present, "configured" if present else "missing"))
    return out


def _check_quality_gates(project_root: Path) -> List[Tuple[str, bool, str]]:
    checks: List[Tuple[str, bool, str]] = []
    d3_path = project_root / "outputs" / "evaluation" / "d3" / "metrics_d3.json"
    d5_path = project_root / "outputs" / "evaluation" / "d3" / "stability_d5.json"
    d6_path = project_root / "outputs" / "evaluation" / "d3" / "calibration_d6.json"

    if d3_path.exists():
        d3 = _read_json(d3_path)
        d3_status = str(d3.get("gate", {}).get("status", "UNKNOWN")).upper()
        checks.append(("D3 quality gate", d3_status == "PASS", d3_status))
    else:
        checks.append(("D3 quality gate", False, "missing metrics_d3.json"))

    if d5_path.exists():
        d5 = _read_json(d5_path)
        d5_status = str(d5.get("stability_gate", {}).get("status", "UNKNOWN")).upper()
        checks.append(("D5 stability gate", d5_status == "PASS", d5_status))
    else:
        checks.append(("D5 stability gate", False, "missing stability_d5.json"))

    if d6_path.exists():
        d6 = _read_json(d6_path)
        d6_status = str(d6.get("readiness_gate", {}).get("status", "UNKNOWN")).upper()
        checks.append(("D6 readiness gate", d6_status == "PASS", d6_status))
    else:
        checks.append(("D6 readiness gate", False, "missing calibration_d6.json"))

    return checks


def _score(items: List[Tuple[str, bool, str]]) -> Tuple[int, int]:
    total = len(items)
    ok = sum(1 for _, status, _ in items if status)
    return ok, total


def _build_report(
    project_root: Path,
    files_checks: List[Tuple[str, bool, str]],
    env_checks: List[Tuple[str, bool, str]],
    gate_checks: List[Tuple[str, bool, str]],
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    all_checks = files_checks + env_checks + gate_checks
    ok, total = _score(all_checks)
    global_status = "PASS" if ok == total else "WARN"

    lines: List[str] = []
    lines.append("# Pre-Soutenance Checklist Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{ts}`")
    lines.append(f"- Project root: `{project_root.as_posix()}`")
    lines.append(f"- Global status: `{global_status}` ({ok}/{total} checks)")
    lines.append("")
    lines.append("## 1) Required files")
    lines.append("")
    for label, status, info in files_checks:
        icon = "PASS" if status else "FAIL"
        lines.append(f"- [{icon}] {label}: `{info}`")
    lines.append("")
    lines.append("## 2) Environment readiness")
    lines.append("")
    for label, status, info in env_checks:
        icon = "PASS" if status else "FAIL"
        lines.append(f"- [{icon}] {label}: `{info}`")
    lines.append("")
    lines.append("## 3) Quality gates")
    lines.append("")
    for label, status, info in gate_checks:
        icon = "PASS" if status else "FAIL"
        lines.append(f"- [{icon}] {label}: `{info}`")
    lines.append("")
    lines.append("## 4) Demo command sequence")
    lines.append("")
    lines.append("```powershell")
    lines.append(".\\scripts\\test_d3.ps1")
    lines.append(".\\scripts\\test_d4_ablation.ps1")
    lines.append(".\\scripts\\test_d5_stability.ps1")
    lines.append(".\\scripts\\test_d6_calibration.ps1")
    lines.append(".\\scripts\\test_e1_pack.ps1")
    lines.append("python -m pytest -c pytest.ini tests_d1 -q")
    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-soutenance final checklist")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-md", default="outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.md")
    parser.add_argument("--output-json", default="outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json")
    parser.add_argument("--enforce-strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    out_md = Path(args.output_md)
    out_json = Path(args.output_json)

    file_checks = _check_required_files(root)
    env_checks = _check_env(root)
    gate_checks = _check_quality_gates(root)
    all_checks = file_checks + env_checks + gate_checks
    ok, total = _score(all_checks)

    report = _build_report(root, file_checks, env_checks, gate_checks)
    payload = {
        "global_status": "PASS" if ok == total else "WARN",
        "ok_checks": ok,
        "total_checks": total,
        "required_files": [{"label": a, "status": b, "info": c} for a, b, c in file_checks],
        "environment": [{"label": a, "status": b, "info": c} for a, b, c in env_checks],
        "quality_gates": [{"label": a, "status": b, "info": c} for a, b, c in gate_checks],
    }

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(report, encoding="utf-8")
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[E2] Checklist report: {out_md}")
    print(f"[E2] Checklist json  : {out_json}")
    print(f"[E2] Status: {payload['global_status']} ({ok}/{total})")

    if args.enforce_strict and ok != total:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
