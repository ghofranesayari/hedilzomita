import argparse
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


def _normalize_skill(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return " ".join(text.strip().lower().split())


def _safe_set(values: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for value in values or []:
        norm = _normalize_skill(value)
        if norm:
            out.add(norm)
    return out


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSONL introuvable: {path}")
    rows: List[Dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON invalide ({path}:{i}) -> {exc}") from exc
    return rows


def _extract_predicted_skills(pred_row: Dict[str, Any]) -> Set[str]:
    if "predicted_hard_skills" in pred_row:
        return _safe_set(pred_row.get("predicted_hard_skills", []))
    predicted = pred_row.get("predicted", {})
    return _safe_set(predicted.get("hard_skills", []))


def _extract_evidence_items(pred_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "evidence_items" in pred_row:
        return pred_row.get("evidence_items", []) or []
    predicted = pred_row.get("predicted", {})
    return predicted.get("evidence", []) or []


def _evidence_supported(item: Dict[str, Any], cv_text: str) -> bool:
    explicit_flag = item.get("supported", None)
    if isinstance(explicit_flag, bool):
        return explicit_flag
    snippet = str(item.get("snippet", "")).strip().lower()
    if not snippet:
        return False
    return snippet in cv_text.lower()


def _prf1(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if (precision + recall) == 0:
        return precision, recall, 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


@dataclass
class Counters:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    unsupported_evidence: int = 0
    total_evidence: int = 0
    false_accept_absent: int = 0
    total_absent_labels: int = 0
    with_prediction: int = 0
    total_samples: int = 0


def evaluate_d3(
    golden_rows: List[Dict[str, Any]],
    prediction_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    pred_by_id = {str(row.get("sample_id", "")).strip(): row for row in prediction_rows}
    counters = Counters(total_samples=len(golden_rows))
    per_sample: List[Dict[str, Any]] = []

    macro_precision_sum = 0.0
    macro_recall_sum = 0.0
    macro_f1_sum = 0.0

    for sample in golden_rows:
        sample_id = str(sample.get("sample_id", "")).strip()
        if not sample_id:
            continue

        gt = sample.get("ground_truth", {})
        cv_text = str(sample.get("cv_text", ""))
        gt_present = _safe_set(gt.get("hard_skills_present", []))
        gt_absent = _safe_set(gt.get("hard_skills_absent", []))

        pred = pred_by_id.get(sample_id, {})
        pred_skills = _extract_predicted_skills(pred)
        evidence_items = _extract_evidence_items(pred)
        if pred:
            counters.with_prediction += 1

        tp = len(gt_present & pred_skills)
        fp = len(pred_skills - gt_present)
        fn = len(gt_present - pred_skills)
        p, r, f1 = _prf1(tp, fp, fn)

        counters.tp += tp
        counters.fp += fp
        counters.fn += fn
        counters.false_accept_absent += len(pred_skills & gt_absent)
        counters.total_absent_labels += len(gt_absent)

        if evidence_items:
            unsupported = sum(0 if _evidence_supported(item, cv_text) else 1 for item in evidence_items)
            total_evidence = len(evidence_items)
        else:
            # Fail-closed: une competence predite sans preuve est consideree non supportee.
            unsupported = len(pred_skills)
            total_evidence = len(pred_skills)
        counters.unsupported_evidence += unsupported
        counters.total_evidence += total_evidence

        macro_precision_sum += p
        macro_recall_sum += r
        macro_f1_sum += f1

        per_sample.append(
            {
                "sample_id": sample_id,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f1, 4),
                "unsupported_evidence_count": unsupported,
                "total_evidence_count": total_evidence,
                "false_accept_absent_count": len(pred_skills & gt_absent),
            }
        )

    micro_p, micro_r, micro_f1 = _prf1(counters.tp, counters.fp, counters.fn)
    n = len(per_sample) if per_sample else 1
    macro_p = macro_precision_sum / n
    macro_r = macro_recall_sum / n
    macro_f1 = macro_f1_sum / n

    unsupported_evidence_rate = (
        counters.unsupported_evidence / counters.total_evidence if counters.total_evidence > 0 else 0.0
    )
    false_claim_acceptance_rate = (
        counters.false_accept_absent / counters.total_absent_labels if counters.total_absent_labels > 0 else 0.0
    )

    return {
        "protocol_version": "d3_v1",
        "summary": {
            "samples_total": counters.total_samples,
            "samples_with_prediction": counters.with_prediction,
            "coverage_rate": round(
                counters.with_prediction / counters.total_samples if counters.total_samples > 0 else 0.0, 4
            ),
            "micro_precision": round(micro_p, 4),
            "micro_recall": round(micro_r, 4),
            "micro_f1": round(micro_f1, 4),
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "macro_f1": round(macro_f1, 4),
            "unsupported_evidence_rate": round(unsupported_evidence_rate, 4),
            "false_claim_acceptance_rate": round(false_claim_acceptance_rate, 4),
        },
        "counters": {
            "tp": counters.tp,
            "fp": counters.fp,
            "fn": counters.fn,
            "unsupported_evidence": counters.unsupported_evidence,
            "total_evidence": counters.total_evidence,
            "false_accept_absent": counters.false_accept_absent,
            "total_absent_labels": counters.total_absent_labels,
        },
        "per_sample": per_sample,
    }


def _build_markdown_report(
    metrics: Dict[str, Any],
    golden_path: Path,
    pred_path: Path,
    json_output_path: Path,
) -> str:
    summary = metrics.get("summary", {})
    gate = metrics.get("gate", {})
    per_sample = metrics.get("per_sample", [])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    lines: List[str] = []
    lines.append("# D3 Evaluation Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append(f"- Protocol: `{metrics.get('protocol_version', 'unknown')}`")
    lines.append(f"- Golden set: `{golden_path.as_posix()}`")
    lines.append(f"- Predictions: `{pred_path.as_posix()}`")
    lines.append(f"- JSON metrics: `{json_output_path.as_posix()}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key in [
        "samples_total",
        "samples_with_prediction",
        "coverage_rate",
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "unsupported_evidence_rate",
        "false_claim_acceptance_rate",
    ]:
        lines.append(f"| `{key}` | `{summary.get(key, 'n/a')}` |")
    lines.append(f"| `gate_status` | `{gate.get('status', 'n/a')}` |")
    lines.append(f"| `gate_reason` | `{gate.get('reason', 'n/a')}` |")
    lines.append("")
    lines.append("## Per-sample details")
    lines.append("")
    lines.append("| Sample | TP | FP | FN | Precision | Recall | F1 | Unsupported Evidence | False Accept Absent |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in per_sample:
        lines.append(
            "| `{sample_id}` | `{tp}` | `{fp}` | `{fn}` | `{precision}` | `{recall}` | `{f1}` | `{unsupported}` | `{false_accept}` |".format(
                sample_id=row.get("sample_id", "n/a"),
                tp=row.get("tp", 0),
                fp=row.get("fp", 0),
                fn=row.get("fn", 0),
                precision=row.get("precision", 0.0),
                recall=row.get("recall", 0.0),
                f1=row.get("f1", 0.0),
                unsupported=row.get("unsupported_evidence_count", 0),
                false_accept=row.get("false_accept_absent_count", 0),
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `unsupported_evidence_rate` measures evidence not supported by CV text.")
    lines.append("- `false_claim_acceptance_rate` measures predicted absent skills accepted as present.")
    lines.append("- Use these metrics for regression tracking between model/prompt versions.")
    lines.append("")
    return "\n".join(lines)


def _evaluate_gate(metrics: Dict[str, Any], min_micro_f1: float) -> Dict[str, Any]:
    micro_f1 = float(metrics.get("summary", {}).get("micro_f1", 0.0))
    passed = micro_f1 >= min_micro_f1
    if passed:
        reason = f"PASS: micro_f1={micro_f1:.4f} >= min_micro_f1={min_micro_f1:.4f}"
    else:
        reason = f"FAIL: micro_f1={micro_f1:.4f} < min_micro_f1={min_micro_f1:.4f}"
    return {
        "status": "PASS" if passed else "FAIL",
        "min_micro_f1": round(min_micro_f1, 4),
        "observed_micro_f1": round(micro_f1, 4),
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="D3 scientific evaluation runner")
    parser.add_argument(
        "--golden",
        default="evaluation/d3/golden_set.template.jsonl",
        help="Path to D3 golden set JSONL",
    )
    parser.add_argument(
        "--predictions",
        default="evaluation/d3/predictions.template.jsonl",
        help="Path to model predictions JSONL",
    )
    parser.add_argument(
        "--output",
        default="outputs/evaluation/d3/metrics_d3.json",
        help="Output metrics JSON path",
    )
    parser.add_argument(
        "--output-md",
        default="outputs/evaluation/d3/report_d3.md",
        help="Output report Markdown path",
    )
    parser.add_argument(
        "--min-micro-f1",
        type=float,
        default=0.65,
        help="Minimum micro-F1 threshold for PASS/FAIL gate",
    )
    parser.add_argument(
        "--enforce-gate",
        action="store_true",
        help="Return non-zero exit code when gate status is FAIL",
    )
    args = parser.parse_args()

    golden_path = Path(args.golden)
    pred_path = Path(args.predictions)
    output_path = Path(args.output)
    output_md_path = Path(args.output_md)

    golden_rows = _load_jsonl(golden_path)
    pred_rows = _load_jsonl(pred_path)
    metrics = evaluate_d3(golden_rows, pred_rows)
    metrics["gate"] = _evaluate_gate(metrics, min_micro_f1=args.min_micro_f1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md = _build_markdown_report(metrics, golden_path, pred_path, output_path)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(report_md, encoding="utf-8")
    print(f"[D3] Metrics written to: {output_path}")
    print(f"[D3] Markdown report written to: {output_md_path}")
    print(f"[D3] Micro-F1: {metrics['summary']['micro_f1']}")
    print(f"[D3] Unsupported Evidence Rate: {metrics['summary']['unsupported_evidence_rate']}")
    print(f"[D3] False Claim Acceptance Rate: {metrics['summary']['false_claim_acceptance_rate']}")
    print(f"[D3] Gate: {metrics['gate']['status']} ({metrics['gate']['reason']})")

    if args.enforce_gate and metrics["gate"]["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
