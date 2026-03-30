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


def build_timeline(total_minutes: int = 15) -> List[Dict[str, Any]]:
    # Fixed structure optimized for a 15-minute master defense demo.
    timeline = [
        {
            "start_min": 0,
            "end_min": 1,
            "title": "Contexte et objectif",
            "say": "Je presente une plateforme d'audit CV pour profils PhD/Postdoc vers industrie, avec garde-fous anti-hallucination.",
            "action": "Afficher la slide 1-page.",
        },
        {
            "start_min": 1,
            "end_min": 3,
            "title": "Probleme scientifique",
            "say": "Le probleme est la traductibilite recherche -> impact industrie, avec preuves verifiables.",
            "action": "Montrer la motivation et les limites des approches heuristiques.",
        },
        {
            "start_min": 3,
            "end_min": 5,
            "title": "Architecture logique (6 couches)",
            "say": "Le systeme combine ingestion, memoire hybride, orchestration LangGraph, agents experts, scoring, et sorties.",
            "action": "Afficher le schema d'architecture.",
        },
        {
            "start_min": 5,
            "end_min": 7,
            "title": "Hardening technique",
            "say": "Nous avons introduit fail-closed, Cypher parametre, integrite d'index, chiffrement PII, et cleanup temp.",
            "action": "Presenter la liste de controles de securite.",
        },
        {
            "start_min": 7,
            "end_min": 9,
            "title": "D3 - Qualite extraction",
            "say": "Je montre precision/recall/F1 et metriques anti-hallucination.",
            "action": "Executer test D3 et ouvrir metrics_d3/report_d3.",
            "command": ".\\scripts\\test_d3.ps1",
        },
        {
            "start_min": 9,
            "end_min": 10,
            "title": "D4 - Ablation",
            "say": "Le baseline doit surpasser les variantes degradees, ce qui valide la contribution des composants.",
            "action": "Executer ablation et montrer le classement des variantes.",
            "command": ".\\scripts\\test_d4_ablation.ps1",
        },
        {
            "start_min": 10,
            "end_min": 11,
            "title": "D5 - Stabilite",
            "say": "Je verifie la repetabilite inter-runs et la variance faible.",
            "action": "Executer stabilite et afficher gate PASS.",
            "command": ".\\scripts\\test_d5_stability.ps1",
        },
        {
            "start_min": 11,
            "end_min": 12,
            "title": "D6 - Calibration finale",
            "say": "Le scorecard final consolide les seuils et donne un readiness gate.",
            "action": "Executer calibration et montrer readiness PASS/FAIL.",
            "command": ".\\scripts\\test_d6_calibration.ps1",
        },
        {
            "start_min": 12,
            "end_min": 13,
            "title": "Checklist avant demo",
            "say": "Je securise la demo avec une checklist automatique pre-soutenance.",
            "action": "Executer checklist et montrer PASS global.",
            "command": ".\\scripts\\test_e2_checklist.ps1",
        },
        {
            "start_min": 13,
            "end_min": 14,
            "title": "Pack de soutenance",
            "say": "Le pack est genere automatiquement avec architecture, securite et validation.",
            "action": "Executer generation pack et ouvrir SOUTENANCE_1PAGE.md.",
            "command": ".\\scripts\\test_e1_pack.ps1",
        },
        {
            "start_min": 14,
            "end_min": 15,
            "title": "Limites et roadmap",
            "say": "La limite principale est la taille du golden set; roadmap: extension dataset et couverture domaines.",
            "action": "Conclure avec plan d'industrialisation et Q&A.",
        },
    ]

    # If user asks shorter than 15 min, trim from the end while keeping key blocks.
    if total_minutes < 15:
        trimmed: List[Dict[str, Any]] = []
        for item in timeline:
            if item["start_min"] >= total_minutes:
                break
            trimmed_item = dict(item)
            trimmed_item["end_min"] = min(item["end_min"], total_minutes)
            trimmed.append(trimmed_item)
        timeline = trimmed

    return timeline


def _build_markdown(
    timeline: List[Dict[str, Any]],
    readiness_status: str,
    checklist_status: str,
    total_minutes: int,
    output_json_path: Path,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: List[str] = []
    lines.append("# Dry-Run Soutenance Script")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{ts}`")
    lines.append(f"- Total duration: `{total_minutes} min`")
    lines.append(f"- D6 readiness status: `{readiness_status}`")
    lines.append(f"- Pre-soutenance checklist: `{checklist_status}`")
    lines.append(f"- JSON script: `{output_json_path.as_posix()}`")
    lines.append("")
    lines.append("## Timeline (minute-by-minute)")
    lines.append("")
    lines.append("| Slot | Segment | What to say | Demo action |")
    lines.append("|---|---|---|---|")
    for item in timeline:
        slot = f"{item['start_min']}-{item['end_min']}"
        lines.append(f"| `{slot}` | {item['title']} | {item['say']} | {item['action']} |")
    lines.append("")
    lines.append("## Command checklist (live demo)")
    lines.append("")
    for item in timeline:
        cmd = item.get("command")
        if cmd:
            lines.append(f"- `{cmd}`")
    lines.append("")
    lines.append("## Fallback protocol")
    lines.append("")
    lines.append("- If a command fails, show latest generated artifact from `outputs/evaluation/d3/`.")
    lines.append("- Keep narrative focused on methodology and validated gates (D3/D4/D5/D6).")
    lines.append("- If API is unavailable, present deterministic and previously generated evidence.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dry-run soutenance script")
    parser.add_argument("--total-minutes", type=int, default=15)
    parser.add_argument("--d6-json", default="outputs/evaluation/d3/calibration_d6.json")
    parser.add_argument("--checklist-json", default="outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json")
    parser.add_argument("--output-md", default="outputs/soutenance/DRY_RUN_SOUTENANCE.md")
    parser.add_argument("--output-json", default="outputs/soutenance/DRY_RUN_SOUTENANCE.json")
    args = parser.parse_args()

    d6 = _load_json_optional(Path(args.d6_json))
    checklist = _load_json_optional(Path(args.checklist_json))
    readiness_status = (
        str(d6.get("readiness_gate", {}).get("status", "UNKNOWN")).upper()
        if d6
        else "UNKNOWN"
    )
    checklist_status = str(checklist.get("global_status", "UNKNOWN")).upper() if checklist else "UNKNOWN"

    timeline = build_timeline(total_minutes=args.total_minutes)
    payload = {
        "protocol_version": "e3_dry_run_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "total_minutes": args.total_minutes,
        "d6_readiness_status": readiness_status,
        "checklist_status": checklist_status,
        "timeline": timeline,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        _build_markdown(
            timeline=timeline,
            readiness_status=readiness_status,
            checklist_status=checklist_status,
            total_minutes=args.total_minutes,
            output_json_path=out_json,
        ),
        encoding="utf-8",
    )

    print(f"[E3] Markdown: {out_md}")
    print(f"[E3] JSON    : {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
