# D3 Scientific Evaluation Protocol (Golden Set)

This folder defines the reproducible evaluation protocol for D3.

## Goal

Measure quality of CV-only analysis with a fixed, auditable ground truth.

## Scope

- Hard-skills extraction quality from CV text
- Evidence support quality (`supported` vs `unsupported`)
- Anti-hallucination behavior (`UNVERIFIED` / missing proof handling)

## Dataset Format

Each sample is one JSON object in `golden_set.jsonl`.

Reference schema: `golden_set.schema.json`.

Starter template: `golden_set.template.jsonl`.

## Mandatory Fields per Sample

- `sample_id`: unique id (`CV_001`, ...)
- `mode`: must be `candidate_cv_only`
- `candidate_profile`: metadata (level/domain)
- `cv_text`: source text used for evaluation
- `ground_truth`: expected labels

## Ground Truth Labels

- `hard_skills_present`: skills explicitly present in CV
- `hard_skills_absent`: skills expected as absent (negative set)
- `evidence_spans`: text snippets used as proof anchors
- `cv_signals`: expected writing-quality signals

## Metrics (implemented in D3.2)

- Precision / Recall / F1 for hard skills
- Unsupported Evidence Rate
- False Claim Acceptance Rate

## Annotation Rules

1. Label only what is explicitly supported by CV text.
2. Do not infer tools/skills from degree title alone.
3. If wording is ambiguous, mark as absent.
4. Evidence span must be copied from CV text (verbatim).

## Reproducibility

- Keep Golden Set versioned in Git.
- Any sample change requires:
  - version bump
  - changelog note
  - re-run D3 metrics

## Execution Commands

PowerShell:

```powershell
.\scripts\test_d3.ps1
```

PowerShell (custom gate threshold):

```powershell
.\scripts\test_d3.ps1 -MinMicroF1 0.70 -EnforceGate $true
```

Batch:

```bat
scripts\test_d3.bat
```

## D4 Ablation Commands

PowerShell:

```powershell
.\scripts\test_d4_ablation.ps1
```

Batch:

```bat
scripts\test_d4_ablation.bat
```

## D5 Stability Commands

PowerShell:

```powershell
.\scripts\test_d5_stability.ps1
```

Batch:

```bat
scripts\test_d5_stability.bat
```

## D6 Calibration Commands

PowerShell:

```powershell
.\scripts\test_d6_calibration.ps1
```

Batch:

```bat
scripts\test_d6_calibration.bat
```

Direct Python:

```powershell
.\.venv\Scripts\python.exe scripts\eval_d3.py `
  --golden evaluation/d3/golden_set.template.jsonl `
  --predictions evaluation/d3/predictions.template.jsonl `
  --output outputs/evaluation/d3/metrics_d3.json `
  --output-md outputs/evaluation/d3/report_d3.md `
  --min-micro-f1 0.65 `
  --enforce-gate
```
