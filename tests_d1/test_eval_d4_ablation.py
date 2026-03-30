import json
from pathlib import Path

from scripts.eval_d3_ablation import run_ablation


def _write_jsonl(path: Path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def test_run_ablation_ranking_and_delta(tmp_path: Path):
    golden_path = tmp_path / "golden.jsonl"
    variants_dir = tmp_path / "variants"
    variants_dir.mkdir(parents=True)

    golden_rows = [
        {
            "sample_id": "CV_A",
            "cv_text": "python and validation",
            "ground_truth": {
                "hard_skills_present": ["python", "validation"],
                "hard_skills_absent": ["aws"],
            },
        }
    ]
    _write_jsonl(golden_path, golden_rows)

    good_variant = [
        {
            "sample_id": "CV_A",
            "predicted_hard_skills": ["python", "validation"],
            "evidence_items": [
                {"skill": "python", "snippet": "python", "supported": True},
                {"skill": "validation", "snippet": "validation", "supported": True},
            ],
        }
    ]
    bad_variant = [
        {
            "sample_id": "CV_A",
            "predicted_hard_skills": ["aws"],
            "evidence_items": [],
        }
    ]

    _write_jsonl(variants_dir / "baseline.jsonl", good_variant)
    _write_jsonl(variants_dir / "noisy.jsonl", bad_variant)

    data = run_ablation(
        golden_path=golden_path,
        variants_dir=variants_dir,
        baseline_name="baseline",
        min_micro_f1=0.65,
    )

    assert data["baseline_variant"] == "baseline"
    assert len(data["variants"]) == 2
    assert data["variants"][0]["variant"] == "baseline"
    assert data["variants"][0]["delta_micro_f1_vs_baseline"] == 0.0
    assert data["variants"][1]["delta_micro_f1_vs_baseline"] < 0.0
