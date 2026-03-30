import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _recommend_thresholds(
    d3_metrics: Dict[str, Any],
    d5_stability: Dict[str, Any],
) -> Dict[str, float]:
    summary = d3_metrics.get("summary", {})
    agg = d5_stability.get("aggregate", {})

    micro_f1 = float(summary.get("micro_f1", 0.0))
    unsupported = float(summary.get("unsupported_evidence_rate", 1.0))
    false_claim = float(summary.get("false_claim_acceptance_rate", 1.0))
    std_micro = float(agg.get("micro_f1", {}).get("std", 0.0))

    rec_min_micro_f1 = max(0.60, round(micro_f1 - 0.05, 4))
    rec_max_unsupported = min(1.0, round(unsupported + 0.05, 4))
    rec_max_false_claim = min(1.0, round(false_claim + 0.05, 4))
    rec_max_std_micro = max(0.005, round(std_micro + 0.01, 4))

    return {
        "min_micro_f1": rec_min_micro_f1,
        "max_unsupported_evidence_rate": rec_max_unsupported,
        "max_false_claim_acceptance_rate": rec_max_false_claim,
        "max_stability_std_micro_f1": rec_max_std_micro,
    }


def _evaluate_readiness(
    d3_metrics: Dict[str, Any],
    d4_ablation: Dict[str, Any],
    d5_stability: Dict[str, Any],
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    summary = d3_metrics.get("summary", {})
    variants = d4_ablation.get("variants", [])
    agg = d5_stability.get("aggregate", {})

    micro_f1 = float(summary.get("micro_f1", 0.0))
    unsupported = float(summary.get("unsupported_evidence_rate", 1.0))
    false_claim = float(summary.get("false_claim_acceptance_rate", 1.0))
    std_micro = float(agg.get("micro_f1", {}).get("std", 1.0))

    has_failing_variant = any(v.get("gate_status") == "FAIL" for v in variants)

    checks = {
        "micro_f1_ok": micro_f1 >= thresholds["min_micro_f1"],
        "unsupported_rate_ok": unsupported <= thresholds["max_unsupported_evidence_rate"],
        "false_claim_rate_ok": false_claim <= thresholds["max_false_claim_acceptance_rate"],
        "stability_std_ok": std_micro <= thresholds["max_stability_std_micro_f1"],
        "ablation_discriminative_ok": has_failing_variant,
    }
    passed = all(checks.values())

    findings: List[str] = []
    if not checks["micro_f1_ok"]:
        findings.append(
            f"Micro-F1 trop faible ({micro_f1:.4f} < {thresholds['min_micro_f1']:.4f})."
        )
    if not checks["unsupported_rate_ok"]:
        findings.append(
            "Unsupported evidence rate trop élevée "
            f"({unsupported:.4f} > {thresholds['max_unsupported_evidence_rate']:.4f})."
        )
    if not checks["false_claim_rate_ok"]:
        findings.append(
            "False claim acceptance rate trop élevée "
            f"({false_claim:.4f} > {thresholds['max_false_claim_acceptance_rate']:.4f})."
        )
    if not checks["stability_std_ok"]:
        findings.append(
            "Variance micro-F1 trop élevée "
            f"(std={std_micro:.6f} > {thresholds['max_stability_std_micro_f1']:.6f})."
        )
    if not checks["ablation_discriminative_ok"]:
        findings.append("Ablation non discriminative: aucun variant FAIL détecté.")

    if passed:
        findings.append("Tous les criteres D6 sont satisfaits.")

    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "findings": findings,
        "observed": {
            "micro_f1": round(micro_f1, 4),
            "unsupported_evidence_rate": round(unsupported, 4),
            "false_claim_acceptance_rate": round(false_claim, 4),
            "stability_std_micro_f1": round(std_micro, 6),
            "ablation_has_fail_variant": has_failing_variant,
        },
    }


def _build_markdown(
    calibration: Dict[str, Any],
    d3_path: Path,
    d4_path: Path,
    d5_path: Path,
    output_json: Path,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    readiness = calibration["readiness_gate"]
    thresholds = calibration["thresholds"]
    obs = readiness["observed"]

    lines: List[str] = []
    lines.append("# D6 Calibration & Readiness Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append(f"- D3 input: `{d3_path.as_posix()}`")
    lines.append(f"- D4 input: `{d4_path.as_posix()}`")
    lines.append(f"- D5 input: `{d5_path.as_posix()}`")
    lines.append(f"- JSON output: `{output_json.as_posix()}`")
    lines.append("")
    lines.append("## Final Gate")
    lines.append("")
    lines.append(f"- Status: `{readiness['status']}`")
    lines.append("")
    lines.append("## Thresholds Used")
    lines.append("")
    lines.append("| Metric | Threshold | Observed |")
    lines.append("|---|---:|---:|")
    lines.append(f"| `min_micro_f1` | `{thresholds['min_micro_f1']}` | `{obs['micro_f1']}` |")
    lines.append(
        f"| `max_unsupported_evidence_rate` | `{thresholds['max_unsupported_evidence_rate']}` | `{obs['unsupported_evidence_rate']}` |"
    )
    lines.append(
        f"| `max_false_claim_acceptance_rate` | `{thresholds['max_false_claim_acceptance_rate']}` | `{obs['false_claim_acceptance_rate']}` |"
    )
    lines.append(
        f"| `max_stability_std_micro_f1` | `{thresholds['max_stability_std_micro_f1']}` | `{obs['stability_std_micro_f1']}` |"
    )
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    for finding in readiness["findings"]:
        lines.append(f"- {finding}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="D6 calibration scorecard")
    parser.add_argument("--d3", default="outputs/evaluation/d3/metrics_d3.json")
    parser.add_argument("--d4", default="outputs/evaluation/d3/ablation_d4.json")
    parser.add_argument("--d5", default="outputs/evaluation/d3/stability_d5.json")
    parser.add_argument("--output-json", default="outputs/evaluation/d3/calibration_d6.json")
    parser.add_argument("--output-md", default="outputs/evaluation/d3/calibration_d6.md")
    parser.add_argument("--enforce-gate", action="store_true")
    args = parser.parse_args()

    d3_path = Path(args.d3)
    d4_path = Path(args.d4)
    d5_path = Path(args.d5)

    d3_metrics = _load_json(d3_path)
    d4_ablation = _load_json(d4_path)
    d5_stability = _load_json(d5_path)

    recommended = _recommend_thresholds(d3_metrics, d5_stability)
    readiness = _evaluate_readiness(d3_metrics, d4_ablation, d5_stability, recommended)
    out = {
        "protocol_version": "d6_calibration_v1",
        "thresholds": recommended,
        "readiness_gate": readiness,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown(out, d3_path, d4_path, d5_path, output_json), encoding="utf-8")

    print(f"[D6] JSON: {output_json}")
    print(f"[D6] MD  : {output_md}")
    print(f"[D6] Readiness gate: {readiness['status']}")

    if args.enforce_gate and readiness["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
