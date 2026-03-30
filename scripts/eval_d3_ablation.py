import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from scripts.eval_d3 import _evaluate_gate, _load_jsonl, evaluate_d3
except ModuleNotFoundError:
    # Support direct execution: python scripts/eval_d3_ablation.py
    from eval_d3 import _evaluate_gate, _load_jsonl, evaluate_d3


def _collect_variant_files(variants_dir: Path) -> List[Path]:
    if not variants_dir.exists():
        raise FileNotFoundError(f"Variants dir introuvable: {variants_dir}")
    files = sorted(variants_dir.glob("*.jsonl"))
    if not files:
        raise ValueError(f"Aucun fichier .jsonl dans {variants_dir}")
    return files


def _build_markdown_report(
    rows: List[Dict[str, Any]],
    baseline_name: str,
    golden_path: Path,
    variants_dir: Path,
    output_json: Path,
    output_csv: Path,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: List[str] = []
    lines.append("# D4 Ablation Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append(f"- Golden set: `{golden_path.as_posix()}`")
    lines.append(f"- Variants dir: `{variants_dir.as_posix()}`")
    lines.append(f"- Baseline variant: `{baseline_name}`")
    lines.append(f"- JSON output: `{output_json.as_posix()}`")
    lines.append(f"- CSV output: `{output_csv.as_posix()}`")
    lines.append("")
    lines.append("## Variant Comparison")
    lines.append("")
    lines.append(
        "| Rank | Variant | Gate | Micro F1 | Delta vs Baseline | Unsupported Evidence Rate | False Claim Acceptance Rate | Coverage |"
    )
    lines.append("|---:|---|---|---:|---:|---:|---:|---:|")
    for i, row in enumerate(rows, start=1):
        lines.append(
            f"| {i} | `{row['variant']}` | `{row['gate_status']}` | `{row['micro_f1']}` | "
            f"`{row['delta_micro_f1_vs_baseline']}` | `{row['unsupported_evidence_rate']}` | "
            f"`{row['false_claim_acceptance_rate']}` | `{row['coverage_rate']}` |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Ranking is sorted by `micro_f1` descending.")
    lines.append("- `delta_micro_f1_vs_baseline` > 0 means improvement over baseline.")
    return "\n".join(lines)


def run_ablation(
    golden_path: Path,
    variants_dir: Path,
    baseline_name: str,
    min_micro_f1: float,
) -> Dict[str, Any]:
    golden_rows = _load_jsonl(golden_path)
    variant_files = _collect_variant_files(variants_dir)

    results: List[Dict[str, Any]] = []
    baseline_micro_f1 = None

    for path in variant_files:
        name = path.stem
        pred_rows = _load_jsonl(path)
        metrics = evaluate_d3(golden_rows, pred_rows)
        gate = _evaluate_gate(metrics, min_micro_f1=min_micro_f1)
        summary = metrics.get("summary", {})
        row = {
            "variant": name,
            "micro_f1": float(summary.get("micro_f1", 0.0)),
            "macro_f1": float(summary.get("macro_f1", 0.0)),
            "micro_precision": float(summary.get("micro_precision", 0.0)),
            "micro_recall": float(summary.get("micro_recall", 0.0)),
            "unsupported_evidence_rate": float(summary.get("unsupported_evidence_rate", 0.0)),
            "false_claim_acceptance_rate": float(summary.get("false_claim_acceptance_rate", 0.0)),
            "coverage_rate": float(summary.get("coverage_rate", 0.0)),
            "gate_status": gate["status"],
            "gate_reason": gate["reason"],
        }
        results.append(row)
        if name == baseline_name:
            baseline_micro_f1 = row["micro_f1"]

    if baseline_micro_f1 is None:
        baseline_micro_f1 = results[0]["micro_f1"]
        baseline_name = results[0]["variant"]

    for row in results:
        row["delta_micro_f1_vs_baseline"] = round(row["micro_f1"] - baseline_micro_f1, 4)

    results.sort(key=lambda x: x["micro_f1"], reverse=True)
    return {
        "protocol_version": "d4_ablation_v1",
        "baseline_variant": baseline_name,
        "min_micro_f1": min_micro_f1,
        "variants": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="D4 ablation study for D3 metrics")
    parser.add_argument("--golden", default="evaluation/d3/golden_set.template.jsonl")
    parser.add_argument("--variants-dir", default="evaluation/d3/variants")
    parser.add_argument("--baseline", default="baseline")
    parser.add_argument("--min-micro-f1", type=float, default=0.65)
    parser.add_argument("--output-json", default="outputs/evaluation/d3/ablation_d4.json")
    parser.add_argument("--output-csv", default="outputs/evaluation/d3/ablation_d4.csv")
    parser.add_argument("--output-md", default="outputs/evaluation/d3/ablation_d4.md")
    args = parser.parse_args()

    golden_path = Path(args.golden)
    variants_dir = Path(args.variants_dir)
    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)

    data = run_ablation(
        golden_path=golden_path,
        variants_dir=variants_dir,
        baseline_name=args.baseline,
        min_micro_f1=args.min_micro_f1,
    )

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "gate_status",
                "micro_f1",
                "delta_micro_f1_vs_baseline",
                "unsupported_evidence_rate",
                "false_claim_acceptance_rate",
                "coverage_rate",
            ],
        )
        writer.writeheader()
        for row in data["variants"]:
            writer.writerow({k: row[k] for k in writer.fieldnames})

    report = _build_markdown_report(
        rows=data["variants"],
        baseline_name=data["baseline_variant"],
        golden_path=golden_path,
        variants_dir=variants_dir,
        output_json=output_json,
        output_csv=output_csv,
    )
    output_md.write_text(report, encoding="utf-8")

    print(f"[D4] JSON: {output_json}")
    print(f"[D4] CSV : {output_csv}")
    print(f"[D4] MD  : {output_md}")
    if data["variants"]:
        top = data["variants"][0]
        print(f"[D4] Top variant: {top['variant']} (micro_f1={top['micro_f1']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
