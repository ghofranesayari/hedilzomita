import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List

try:
    from scripts.eval_d3 import _evaluate_gate, _load_jsonl, evaluate_d3
except ModuleNotFoundError:
    from eval_d3 import _evaluate_gate, _load_jsonl, evaluate_d3


def _series_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": round(mean(values), 6),
        "std": round(pstdev(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def _evaluate_stability_gate(
    summary: Dict[str, Any],
    max_std_micro_f1: float,
    max_std_unsupported_rate: float,
    max_std_false_claim_rate: float,
) -> Dict[str, Any]:
    std_micro_f1 = float(summary["micro_f1"]["std"])
    std_unsupported = float(summary["unsupported_evidence_rate"]["std"])
    std_false_claim = float(summary["false_claim_acceptance_rate"]["std"])

    checks = {
        "micro_f1_std_ok": std_micro_f1 <= max_std_micro_f1,
        "unsupported_rate_std_ok": std_unsupported <= max_std_unsupported_rate,
        "false_claim_rate_std_ok": std_false_claim <= max_std_false_claim_rate,
    }
    passed = all(checks.values())
    reason = (
        "PASS: stability variance thresholds satisfied."
        if passed
        else (
            f"FAIL: std_micro_f1={std_micro_f1:.6f}, "
            f"std_unsupported={std_unsupported:.6f}, std_false_claim={std_false_claim:.6f}"
        )
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "reason": reason,
        "thresholds": {
            "max_std_micro_f1": max_std_micro_f1,
            "max_std_unsupported_rate": max_std_unsupported_rate,
            "max_std_false_claim_rate": max_std_false_claim_rate,
        },
        "checks": checks,
    }


def run_stability(
    golden_path: Path,
    predictions_path: Path,
    runs: int,
    min_micro_f1: float,
    max_std_micro_f1: float,
    max_std_unsupported_rate: float,
    max_std_false_claim_rate: float,
) -> Dict[str, Any]:
    if runs < 2:
        raise ValueError("runs doit être >= 2 pour une mesure de stabilité.")

    golden_rows = _load_jsonl(golden_path)
    pred_rows = _load_jsonl(predictions_path)

    per_run: List[Dict[str, Any]] = []
    micro_f1_values: List[float] = []
    unsupported_values: List[float] = []
    false_claim_values: List[float] = []

    for run_id in range(1, runs + 1):
        metrics = evaluate_d3(golden_rows, pred_rows)
        gate_quality = _evaluate_gate(metrics, min_micro_f1=min_micro_f1)
        summary = metrics["summary"]

        micro_f1 = float(summary["micro_f1"])
        unsupported_rate = float(summary["unsupported_evidence_rate"])
        false_claim_rate = float(summary["false_claim_acceptance_rate"])

        micro_f1_values.append(micro_f1)
        unsupported_values.append(unsupported_rate)
        false_claim_values.append(false_claim_rate)

        per_run.append(
            {
                "run_id": run_id,
                "micro_f1": micro_f1,
                "unsupported_evidence_rate": unsupported_rate,
                "false_claim_acceptance_rate": false_claim_rate,
                "quality_gate_status": gate_quality["status"],
            }
        )

    aggregate = {
        "micro_f1": _series_stats(micro_f1_values),
        "unsupported_evidence_rate": _series_stats(unsupported_values),
        "false_claim_acceptance_rate": _series_stats(false_claim_values),
    }

    stability_gate = _evaluate_stability_gate(
        summary=aggregate,
        max_std_micro_f1=max_std_micro_f1,
        max_std_unsupported_rate=max_std_unsupported_rate,
        max_std_false_claim_rate=max_std_false_claim_rate,
    )

    return {
        "protocol_version": "d5_stability_v1",
        "runs": runs,
        "inputs": {
            "golden_path": golden_path.as_posix(),
            "predictions_path": predictions_path.as_posix(),
        },
        "aggregate": aggregate,
        "stability_gate": stability_gate,
        "per_run": per_run,
    }


def _build_markdown_report(data: Dict[str, Any], output_json: Path) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    agg = data["aggregate"]
    gate = data["stability_gate"]

    lines: List[str] = []
    lines.append("# D5 Stability Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append(f"- Protocol: `{data.get('protocol_version', 'unknown')}`")
    lines.append(f"- Runs: `{data.get('runs', 0)}`")
    lines.append(f"- Golden set: `{data['inputs']['golden_path']}`")
    lines.append(f"- Predictions: `{data['inputs']['predictions_path']}`")
    lines.append(f"- JSON output: `{output_json.as_posix()}`")
    lines.append("")
    lines.append("## Aggregate Statistics")
    lines.append("")
    lines.append("| Metric | Mean | Std | Min | Max |")
    lines.append("|---|---:|---:|---:|---:|")
    for metric_name in ["micro_f1", "unsupported_evidence_rate", "false_claim_acceptance_rate"]:
        m = agg[metric_name]
        lines.append(f"| `{metric_name}` | `{m['mean']}` | `{m['std']}` | `{m['min']}` | `{m['max']}` |")
    lines.append("")
    lines.append("## Stability Gate")
    lines.append("")
    lines.append(f"- Status: `{gate['status']}`")
    lines.append(f"- Reason: `{gate['reason']}`")
    lines.append("")
    lines.append("## Per-run snapshot")
    lines.append("")
    lines.append("| Run | Micro F1 | Unsupported Evidence Rate | False Claim Acceptance Rate | Quality Gate |")
    lines.append("|---:|---:|---:|---:|---|")
    for row in data["per_run"]:
        lines.append(
            f"| {row['run_id']} | {row['micro_f1']} | {row['unsupported_evidence_rate']} | "
            f"{row['false_claim_acceptance_rate']} | {row['quality_gate_status']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="D5 stability/repeatability runner")
    parser.add_argument("--golden", default="evaluation/d3/golden_set.template.jsonl")
    parser.add_argument("--predictions", default="evaluation/d3/predictions.template.jsonl")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--min-micro-f1", type=float, default=0.65)
    parser.add_argument("--max-std-micro-f1", type=float, default=0.02)
    parser.add_argument("--max-std-unsupported-rate", type=float, default=0.02)
    parser.add_argument("--max-std-false-claim-rate", type=float, default=0.02)
    parser.add_argument("--output-json", default="outputs/evaluation/d3/stability_d5.json")
    parser.add_argument("--output-md", default="outputs/evaluation/d3/stability_d5.md")
    parser.add_argument("--enforce-gate", action="store_true")
    args = parser.parse_args()

    data = run_stability(
        golden_path=Path(args.golden),
        predictions_path=Path(args.predictions),
        runs=args.runs,
        min_micro_f1=args.min_micro_f1,
        max_std_micro_f1=args.max_std_micro_f1,
        max_std_unsupported_rate=args.max_std_unsupported_rate,
        max_std_false_claim_rate=args.max_std_false_claim_rate,
    )

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown_report(data, output_json), encoding="utf-8")

    print(f"[D5] JSON: {output_json}")
    print(f"[D5] MD  : {output_md}")
    print(
        "[D5] Stability gate: "
        f"{data['stability_gate']['status']} ({data['stability_gate']['reason']})"
    )

    if args.enforce_gate and data["stability_gate"]["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
