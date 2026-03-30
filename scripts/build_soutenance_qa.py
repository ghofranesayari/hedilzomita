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


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _build_qa_markdown(d3: Dict[str, Any], d5: Dict[str, Any], d6: Dict[str, Any]) -> str:
    d3s = d3.get("summary", {})
    d3g = d3.get("gate", {})
    d5g = d5.get("stability_gate", {})
    d6g = d6.get("readiness_gate", {})
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    micro_f1 = _fmt(d3s.get("micro_f1", 0.0))
    unsupported = _fmt(d3s.get("unsupported_evidence_rate", 0.0))
    false_claim = _fmt(d3s.get("false_claim_acceptance_rate", 0.0))
    d3_status = str(d3g.get("status", "UNKNOWN")).upper()
    d5_status = str(d5g.get("status", "UNKNOWN")).upper()
    d6_status = str(d6g.get("status", "UNKNOWN")).upper()

    lines: List[str] = []
    lines.append("# Q&A Jury - Soutenance")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{generated}`")
    lines.append("")
    lines.append("## Questions et reponses pretes")
    lines.append("")
    lines.append("### Q1. Quelle est la contribution scientifique principale ?")
    lines.append(
        "Une pipeline agentique avec garde-fous anti-hallucination et validation en 4 gates (D3-D6), "
        "au lieu d un simple scoring heuristique."
    )
    lines.append("")
    lines.append("### Q2. Comment prouvez-vous que le modele n hallucine pas ?")
    lines.append(
        f"Par metriques explicites: unsupported_evidence_rate={unsupported}, "
        f"false_claim_acceptance_rate={false_claim}, plus fail-closed en cas d erreur LLM."
    )
    lines.append("")
    lines.append("### Q3. Pourquoi utiliser LangGraph ici ?")
    lines.append(
        "Pour orchestrer proprement les agents par mode (interne vs candidat), tracer les branches, "
        "et imposer des points d agregation et gates verifiables."
    )
    lines.append("")
    lines.append("### Q4. Comment gerez-vous les risques securite ?")
    lines.append(
        "Cypher parametre, vault PII chiffre FR/EN, controle d integrite des index (SHA256), "
        "et cleanup des fichiers temporaires."
    )
    lines.append("")
    lines.append("### Q5. Comment garantissez-vous la reproductibilite ?")
    lines.append(
        f"Tests automatises + stabilite D5 (status={d5_status}) + "
        f"scorecard D6 (status={d6_status}) + scripts de re-run complets."
    )
    lines.append("")
    lines.append("### Q6. Quel est le niveau actuel de performance ?")
    lines.append(
        f"Micro-F1 D3={micro_f1} sur le golden set courant. "
        f"Les gates D3={d3_status}, D5={d5_status} et D6={d6_status}."
    )
    lines.append("")
    lines.append("### Q7. Quelle est la principale limite actuelle ?")
    lines.append(
        "La taille du golden set est encore limitee. L axe prioritaire est d augmenter le corpus annote "
        "pour renforcer la validite externe."
    )
    lines.append("")
    lines.append("### Q8. Pourquoi garder un composant deterministe si vous utilisez un LLM ?")
    lines.append(
        "Le deterministe sert de garde-fou et de base defendable; le LLM enrichit, "
        "mais ne doit pas casser les contraintes de preuve."
    )
    lines.append("")
    lines.append("### Q9. Si l API LLM tombe pendant la demo, que se passe-t-il ?")
    lines.append(
        "Le systeme reste exploitable en mode securise (fail-closed), et la soutenance s appuie sur "
        "les artefacts deja generes (D3-D6, pack E1/E2/E3)."
    )
    lines.append("")
    lines.append("### Q10. Quelle roadmap apres soutenance ?")
    lines.append(
        "Extension du golden set multi-domaines, calibration des seuils par cohorte, "
        "et suivi longitudinal des erreurs par type de profil."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build jury Q&A pack from evaluation artifacts")
    parser.add_argument("--d3", default="outputs/evaluation/d3/metrics_d3.json")
    parser.add_argument("--d5", default="outputs/evaluation/d3/stability_d5.json")
    parser.add_argument("--d6", default="outputs/evaluation/d3/calibration_d6.json")
    parser.add_argument("--output-md", default="outputs/soutenance/QA_JURY.md")
    args = parser.parse_args()

    d3 = _load_json_optional(Path(args.d3))
    d5 = _load_json_optional(Path(args.d5))
    d6 = _load_json_optional(Path(args.d6))

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(_build_qa_markdown(d3=d3, d5=d5, d6=d6), encoding="utf-8")

    print(f"[E4] Markdown: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
