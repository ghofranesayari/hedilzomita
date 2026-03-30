import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _architecture_mermaid() -> str:
    return """flowchart TD
    U["Utilisateur"] --> UI["UI Streamlit"]
    UI --> M{"Mode"}
    M -->|Interne| IN["Flux interne"]
    M -->|Candidat| CA["Flux candidat CV-only"]

    subgraph L1["Couche 1 - Ingestion"]
      P["Parser CV/Offre"]
      G["PII Guard FR/EN + Vault chiffre"]
      R["Routing vers state LangGraph"]
    end

    subgraph L2["Couche 2 - Memoire & Retrieval"]
      V["FAISS + BM25"]
      N["Neo4j Ontologie"]
      H["HyDE (optionnel retrieval)"]
    end

    subgraph L3["Couche 3 - Orchestration"]
      O["LangGraph nodes + router conditionnel"]
    end

    subgraph L4["Couche 4 - Agents"]
      A1["Bridge Hard Skills"]
      A2["Auditor Fail-Closed"]
      A3["CV Global Advisor"]
      A4["Role Recommender"]
      A5["Psycho/Rhetoric/Logistics (mode interne)"]
    end

    subgraph L5["Couche 5 - Scoring"]
      S["Global scorer conditionnel par mode"]
      E["D3/D4/D5/D6 evaluation gates"]
    end

    subgraph L6["Couche 6 - Sorties"]
      O1["UI tabs + export JSON/Markdown"]
      O2["Pack soutenance"]
    end

    IN --> P
    CA --> P
    P --> G --> R --> O
    O --> A1 --> A2
    O --> A3
    O --> A4
    O --> A5
    A2 --> N
    A1 --> V
    V --> H
    A1 --> S
    A2 --> S
    A3 --> S
    A4 --> S
    S --> E --> O1 --> O2
"""


def _one_pager(
    d3: Dict[str, Any],
    d4: Dict[str, Any],
    d5: Dict[str, Any],
    d6: Dict[str, Any],
) -> str:
    d3s = d3.get("summary", {})
    d3g = d3.get("gate", {})
    d5g = d5.get("stability_gate", {})
    d6g = d6.get("readiness_gate", {})
    top_variant = (d4.get("variants") or [{}])[0]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    lines: List[str] = []
    lines.append("# AEBM - Soutenance 1 Page (Architecture + Validation)")
    lines.append("")
    lines.append(f"- Generated (UTC): `{generated}`")
    lines.append("")
    lines.append("## 1) Problem and contribution")
    lines.append("- Goal: robust CV audit for PhD/Postdoc -> industry transition.")
    lines.append("- Core contribution: hybrid agentic pipeline with anti-hallucination controls.")
    lines.append("- Two operating modes: Internal hiring flow and Candidate CV-only flow.")
    lines.append("")
    lines.append("## 2) Logical architecture (6 layers)")
    lines.append("- Ingestion: parsing, PII guard, state initialization.")
    lines.append("- Memory/Retrieval: FAISS + BM25 + Neo4j ontology.")
    lines.append("- Orchestration: LangGraph conditional routing by mode.")
    lines.append("- Agents: bridge, auditor, CV global advisor, role recommender.")
    lines.append("- Scoring: mode-aware scoring + deterministic/LLM controls.")
    lines.append("- Outputs: Streamlit UI, Markdown/JSON reports, evaluation artifacts.")
    lines.append("")
    lines.append("## 3) Engineering hardening done")
    lines.append("- Unique thread ids per run/session (state collision mitigation).")
    lines.append("- Auditor fail-closed (no auto-validation on LLM failures).")
    lines.append("- Neo4j Cypher parameterization (no string-injected queries).")
    lines.append("- Vector store integrity manifest with SHA256 verification.")
    lines.append("- FR/EN PII detection + encrypted vault handling.")
    lines.append("- Temp files retention and cleanup policy.")
    lines.append("")
    lines.append("## 4) Scientific validation status")
    lines.append(f"- D3 quality gate: `{d3g.get('status', 'n/a')}` (micro_f1={_fmt(d3s.get('micro_f1', 0.0))}).")
    lines.append(
        f"- D4 ablation top variant: `{top_variant.get('variant', 'n/a')}` "
        f"(micro_f1={_fmt(top_variant.get('micro_f1', 0.0))})."
    )
    lines.append(f"- D5 stability gate: `{d5g.get('status', 'n/a')}`.")
    lines.append(f"- D6 readiness gate (final): `{d6g.get('status', 'n/a')}`.")
    lines.append("")
    lines.append("## 5) Current quantitative snapshot")
    lines.append(f"- micro_precision: `{_fmt(d3s.get('micro_precision', 0.0))}`")
    lines.append(f"- micro_recall: `{_fmt(d3s.get('micro_recall', 0.0))}`")
    lines.append(f"- micro_f1: `{_fmt(d3s.get('micro_f1', 0.0))}`")
    lines.append(f"- unsupported_evidence_rate: `{_fmt(d3s.get('unsupported_evidence_rate', 0.0))}`")
    lines.append(f"- false_claim_acceptance_rate: `{_fmt(d3s.get('false_claim_acceptance_rate', 0.0))}`")
    lines.append("")
    lines.append("## 6) Limits and next step")
    lines.append("- Golden set currently small; scale to real annotated dataset for stronger external validity.")
    lines.append("- Next step: expand domain coverage and re-run D3-D6 automatically in CI.")
    return "\n".join(lines)


def _detailed_pack(
    d3: Dict[str, Any],
    d4: Dict[str, Any],
    d5: Dict[str, Any],
    d6: Dict[str, Any],
) -> str:
    lines: List[str] = []
    lines.append("# AEBM - Soutenance Technical Pack")
    lines.append("")
    lines.append("## A. Architecture")
    lines.append("### A.1 Mermaid logical view")
    lines.append("```mermaid")
    lines.append(_architecture_mermaid())
    lines.append("```")
    lines.append("")
    lines.append("### A.2 Two-mode behavior in LangGraph")
    lines.append("- Internal mode: full fan-out (psycho + rhetoric + logistics + cv_global).")
    lines.append("- Candidate mode: CV-focused fan-out (cv_global + role_recommender).")
    lines.append("- Aggregator checks are mode-aware to avoid false missing-branch alarms.")
    lines.append("")
    lines.append("## B. Safety and robustness controls")
    lines.append("- Fail-closed auditing on LLM errors.")
    lines.append("- Encrypted PII vault and FR/EN detection.")
    lines.append("- Cypher parameterized queries.")
    lines.append("- Integrity verification for retrieval artifacts.")
    lines.append("- Temp files lifecycle control.")
    lines.append("")
    lines.append("## C. Validation protocol summary")
    lines.append("- D3: extraction quality + anti-hallucination metrics.")
    lines.append("- D4: ablation discrimination (baseline vs degraded variants).")
    lines.append("- D5: repeatability/stability over multiple runs.")
    lines.append("- D6: calibration scorecard with final readiness gate.")
    lines.append("")
    lines.append("## D. Latest results")
    lines.append("```json")
    lines.append(json.dumps({"d3": d3.get("summary", {}), "d6_readiness": d6.get("readiness_gate", {})}, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## E. Reproduction commands")
    lines.append("```powershell")
    lines.append(".\\scripts\\test_d3.ps1")
    lines.append(".\\scripts\\test_d4_ablation.ps1")
    lines.append(".\\scripts\\test_d5_stability.ps1")
    lines.append(".\\scripts\\test_d6_calibration.ps1")
    lines.append("python -m pytest -c pytest.ini tests_d1 -q")
    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build soutenance pack from D3-D6 outputs")
    parser.add_argument("--d3", default="outputs/evaluation/d3/metrics_d3.json")
    parser.add_argument("--d4", default="outputs/evaluation/d3/ablation_d4.json")
    parser.add_argument("--d5", default="outputs/evaluation/d3/stability_d5.json")
    parser.add_argument("--d6", default="outputs/evaluation/d3/calibration_d6.json")
    parser.add_argument("--out-dir", default="outputs/soutenance")
    args = parser.parse_args()

    d3 = _load_json(Path(args.d3))
    d4 = _load_json(Path(args.d4))
    d5 = _load_json(Path(args.d5))
    d6 = _load_json(Path(args.d6))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    one_pager = out_dir / "SOUTENANCE_1PAGE.md"
    detailed = out_dir / "SOUTENANCE_DETAILLEE.md"
    mermaid = out_dir / "SOUTENANCE_ARCHITECTURE.mmd"

    one_pager.write_text(_one_pager(d3, d4, d5, d6), encoding="utf-8")
    detailed.write_text(_detailed_pack(d3, d4, d5, d6), encoding="utf-8")
    mermaid.write_text(_architecture_mermaid(), encoding="utf-8")

    print(f"[E1] Generated: {one_pager}")
    print(f"[E1] Generated: {detailed}")
    print(f"[E1] Generated: {mermaid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
