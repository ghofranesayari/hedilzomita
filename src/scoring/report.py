import json
import os
from pathlib import Path
from typing import Dict

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover
    Fernet = None
    InvalidToken = Exception


class ReportGenerator:
    def __init__(self, vault_path: str = "data/vault/vault.json"):
        self.vault_path = vault_path
        self.vault = self._load_vault()

    def _init_cipher(self, vault_path: str):
        if Fernet is None:
            return None

        key_env = os.getenv("PII_VAULT_KEY", "").strip()
        key_path = Path(
            os.getenv(
                "PII_VAULT_KEY_PATH",
                str(Path(vault_path).with_suffix(".key")),
            )
        )

        try:
            if key_env:
                return Fernet(key_env.encode("utf-8"))
            if key_path.exists():
                return Fernet(key_path.read_bytes().strip())
        except Exception:
            return None
        return None

    def _load_vault(self) -> Dict:
        if not os.path.exists(self.vault_path):
            return {}

        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return {}

        if not isinstance(payload, dict):
            return {}

        if payload.get("vault_format") == "fernet_v1":
            cipher = self._init_cipher(self.vault_path)
            if not cipher:
                return {}
            token = str(payload.get("ciphertext", ""))
            if not token:
                return {}
            try:
                clear = cipher.decrypt(token.encode("utf-8"))
                data = json.loads(clear.decode("utf-8"))
                return data if isinstance(data, dict) else {}
            except InvalidToken:
                return {}
            except Exception:
                return {}

        return payload

    def get_real_name(self, candidate_id: str) -> str:
        return self.vault.get(candidate_id, f"Candidat {candidate_id}")

    def generate_markdown_report(self, state: Dict, output_dir: str = "outputs/reports/"):
        os.makedirs(output_dir, exist_ok=True)

        candidate_id = state.get("candidate_id", "ID_ERROR")
        real_name = self.get_real_name(candidate_id)
        job_title = state.get("job_metadata", {}).get("title", "Poste non specifie")

        diagnostic = state.get("readiness_diagnostic") or {}
        score_10 = diagnostic.get("score_out_of_10", 0.0)
        verdict = diagnostic.get("expert_verdict", "Evaluation technique non generee.")
        cv_summary = diagnostic.get("cv_expert_summary", "")
        cto_details = diagnostic.get("tech_details", {})
        dimensions = diagnostic.get("dimensions", {})

        tech_data = state.get("tech_analysis") or []
        valid_skills = [
            s
            for s in tech_data
            if s.get("audit_status") == "VALIDATED" or s.get("status") == "INFERRED"
        ]

        psycho_data = state.get("psychometrics") or {}
        comm_data = state.get("rhetoric_analysis") or {}
        log_data = state.get("logistics_analysis") or {}
        cv_global_data = state.get("cv_global_analysis") or diagnostic.get("cv_details", {}) or {}
        career_data = state.get("role_recommendations") or diagnostic.get("career_details", {}) or {}

        md = "# RAPPORT D'EVALUATION EXECUTIF\n\n"
        md += f"**Candidat :** {real_name} (`{candidate_id}`)\n"
        md += f"**Poste cible :** {job_title}\n"
        md += "---\n\n"

        md += "## SYNTHESE DECISIONNELLE\n\n"
        md += f"> **FINAL READINESS SCORE : {score_10} / 10**\n\n"
        md += "### Ponderation des piliers\n"
        for dim, score in dimensions.items():
            md += f"- **{dim}** : {score}/10\n"
        md += f"\n> *Verdict technique:* {verdict}\n"
        if cv_summary:
            md += f"> *Lecture CV industrie:* {cv_summary}\n"
        md += "\n---\n\n"

        md += "## 1. FAISABILITE LOGISTIQUE ET PREFERENCES\n\n"
        decision = log_data.get("decision_recommendation", "UNKNOWN")
        md += (
            f"**Recommandation : {decision}** "
            f"(Score : {log_data.get('global_feasibility_score', 0.0)}/10)\n\n"
        )
        for flag in log_data.get("flags", []):
            status = flag.get("status", "INFO")
            icon = "OK" if status in {"MATCH", "BONUS"} else "WARN" if status in {"WARNING", "INFO"} else "KO"
            md += f"- [{icon}] **[{flag.get('category', 'N/A')}]** : {flag.get('details', '')}\n"
        md += "\n---\n\n"

        md += "## 2. MATURITE OPERATIONNELLE (HARD SKILLS)\n\n"
        md += "### Matrice d'evaluation (1 a 5)\n"
        for dim_key in ["transferability", "pragmatism", "complexity"]:
            dim = cto_details.get(dim_key, {})
            if not dim:
                continue
            md += f"- **{dim_key.upper()} ({dim.get('score', 0)}/5) - {dim.get('label', '')}**\n"
            md += f"  - *Justification :* {dim.get('argument', 'N/A')}\n"
            md += f"  - *Preuve :* \"{dim.get('proof', 'N/A')}\"\n\n"

        md += "### Inventaire des competences validees\n"
        for skill in valid_skills:
            status_icon = "TXT" if skill.get("source") == "CV_TEXT" else "INF"
            md += f"- [{status_icon}] **{skill.get('skill_name', 'N/A')}**\n"
            if skill.get("source") == "GRAPH_INFERENCE":
                md += f"  - *Inference ontologique :* {skill.get('audit_comment', 'Deduit logiquement.')}\n"
        md += "\n---\n\n"

        md += "## 3. FIT PSYCHOMETRIQUE (OCEAN)\n\n"
        md += f"**Score d'alignement : {psycho_data.get('job_alignment_score', 0.0)} / 10**\n\n"
        breakdown = psycho_data.get("scoring_breakdown", {})
        if breakdown:
            md += "### Detail du calcul\n"
            md += f"- Base (cosinus) : {breakdown.get('base_match_cosine', 10.0)}/10\n"
            md += f"- Penalite distance : -{breakdown.get('total_distance_penalty', 0.0)}\n"
            md += f"- Plus grand ecart : {breakdown.get('biggest_gap_detected', 'Aucun')}\n"
            if breakdown.get("cognitive_dissonance_flag"):
                md += (
                    "- Alerte dissonance cognitive : "
                    f"-{breakdown.get('cognitive_dissonance_penalty', 0.0)}\n"
                )
            md += "\n"

        md += "### Analyse des traits\n"
        trait_names = {
            "O": "Ouverture",
            "C": "Conscience",
            "E": "Extraversion",
            "A": "Agreabilite",
            "N": "Stabilite emotionnelle",
        }
        for trait_key, details in (psycho_data.get("candidate_analysis", {}) or {}).items():
            full_name = trait_names.get(trait_key, trait_key)
            md += f"- **[{trait_key}] {full_name} ({details.get('score', 0)}/5)**\n"
            reasoning = details.get("reasoning", "N/A")
            md += f"  - {reasoning}\n"
            md += f"  - *Citation :* \"{details.get('quote', 'N/A')}\"\n"
        md += "\n---\n\n"

        md += "## 4. RHETORIQUE ET FORCE DE CONVICTION\n\n"
        md += f"**Score communication : {comm_data.get('communication_score', 0.0)} / 10**\n\n"
        tonal = comm_data.get("tonal_analysis", {})
        if tonal:
            md += (
                f"- **Voix :** {tonal.get('voice_type', 'N/A')} | "
                f"**Clarte :** {tonal.get('clarity_score', 0)}/5 | "
                f"**Persuasion :** {tonal.get('persuasion_score', 0)}/5\n"
            )
            md += f"- **Jargon detecte :** {', '.join(tonal.get('detected_jargon', ['Aucun']))}\n\n"

        md += "### Methode STAR\n"
        for star_key in ["Situation", "Task", "Action", "Result"]:
            star = comm_data.get("star_breakdown", {}).get(star_key, {})
            if star:
                presence = "Present" if star.get("present") else "Absent"
                md += (
                    f"- **{star_key}** [{presence} - Qualite {star.get('quality', 'LOW')}] : "
                    f"{star.get('reasoning', '')}\n"
                )
        md += f"\n> **Resume rhetorique :** {comm_data.get('feedback_summary', 'N/A')}\n"
        advice_list = comm_data.get("improvement_advice", [])
        if advice_list:
            md += "\n### Conseils de reecriture du pitch\n"
            for i, advice in enumerate(advice_list, 1):
                md += f"{i}. {advice}\n"
        md += "\n---\n\n"

        md += "## 5. QUALITE GLOBALE DU CV INDUSTRIE\n\n"
        md += f"**Score CV industrie : {cv_global_data.get('overall_score', 0.0)} / 10**\n"
        md += (
            f"**Positionnement : {cv_global_data.get('profile_positioning', 'N/A')}** "
            f"(Confiance: {cv_global_data.get('confidence', 0.0)})\n\n"
        )
        md += "### Rubric CV\n"
        md += f"- Industry relevance: {cv_global_data.get('industry_relevance', 0.0)}/10\n"
        md += f"- Business impact: {cv_global_data.get('business_impact', 0.0)}/10\n"
        md += f"- Transferability narrative: {cv_global_data.get('transferability_narrative', 0.0)}/10\n"
        md += f"- Brevity focus: {cv_global_data.get('brevity_focus', 0.0)}/10\n"
        md += f"- Publication calibration: {cv_global_data.get('publication_calibration', 0.0)}/10\n"
        md += f"- Evidence quality: {cv_global_data.get('evidence_quality', 0.0)}/10\n\n"

        style_flags = cv_global_data.get("cv_style_flags", {})
        if style_flags:
            md += "### Signaux de style detectes\n"
            md += (
                "- Densite publications elevee: "
                f"{style_flags.get('high_publication_density', False)}\n"
            )
            md += (
                "- Densite metriques business faible: "
                f"{style_flags.get('low_business_metric_density', False)}\n"
            )
            md += (
                "- Compteurs: publications="
                f"{style_flags.get('publication_signal_count', 0)}, "
                f"business_metrics={style_flags.get('business_metric_signal_count', 0)}\n\n"
            )

        risks = cv_global_data.get("critical_risks", [])
        if risks:
            md += "### Risques critiques\n"
            for risk in risks:
                md += f"- **[{risk.get('severity', 'LOW')}] {risk.get('title', 'Risque')}**\n"
                md += f"  - *Preuve:* \"{risk.get('evidence', 'N/A')}\"\n"
                md += f"  - *Impact:* {risk.get('why_it_hurts', 'N/A')}\n"
            md += "\n"

        actions = cv_global_data.get("priority_actions", [])
        if actions:
            md += "### Plan de correction priorise\n"
            for action in sorted(actions, key=lambda a: a.get("priority", 99)):
                md += f"- **P{action.get('priority', '?')} - {action.get('action', 'Action')}**\n"
                md += f"  - *Pourquoi:* {action.get('rationale', 'N/A')}\n"
                if action.get("example_rewrite"):
                    md += f"  - *Exemple:* {action.get('example_rewrite')}\n"
            md += "\n"

        candidate_id = state.get("candidate_id", diagnostic.get("candidate_id", ""))
        if candidate_id == "SELF_AUDIT_USER":
            md += "---\n\n"
            md += "## 6. CAREER FIT ET PLAN DE TRANSITION\n\n"
            immediate = career_data.get("top_immediate_fit", [])
            near_fit = career_data.get("top_near_fit", [])
            no_go = career_data.get("no_go_roles", [])
            action_306090 = career_data.get("action_plan_30_60_90", {})

            md += "### Top postes (fit immediat)\n"
            if immediate:
                for i, rec in enumerate(immediate[:10], 1):
                    md += (
                        f"{i}. **{rec.get('role_title', 'N/A')}** "
                        f"({rec.get('sector', 'N/A')}) - Score {rec.get('match_score', 0)}/100 | "
                        f"Confiance {rec.get('confidence', 0)}\n"
                    )
                    evidences = rec.get("why_match", [])
                    for ev in evidences[:2]:
                        md += f"   - Preuve: \"{ev.get('evidence', 'non demontre')}\"\n"
            else:
                md += "- Aucun role en fit immediat.\n"
            md += "\n"

            md += "### Top postes (fit proche avec gaps)\n"
            if near_fit:
                for i, rec in enumerate(near_fit[:10], 1):
                    md += (
                        f"{i}. **{rec.get('role_title', 'N/A')}** - Score {rec.get('match_score', 0)}/100 | "
                        f"Gaps: {', '.join(rec.get('gaps', [])[:3]) if rec.get('gaps') else 'non demontre'}\n"
                    )
            else:
                md += "- Aucun role en fit proche.\n"
            md += "\n"

            md += "### No-go roles (pour le moment)\n"
            if no_go:
                for i, rec in enumerate(no_go[:10], 1):
                    md += (
                        f"{i}. **{rec.get('role_title', 'N/A')}** - {rec.get('why_not_now', 'non demontre')} "
                        f"(Confiance {rec.get('confidence', 0)})\n"
                    )
            else:
                md += "- Aucun no-go critique detecte.\n"
            md += "\n"

            md += "### Plan d'action 30 / 60 / 90 jours\n"
            for label, items in [
                ("30 jours", action_306090.get("30_days", [])),
                ("60 jours", action_306090.get("60_days", [])),
                ("90 jours", action_306090.get("90_days", [])),
            ]:
                md += f"- **{label}**\n"
                if items:
                    for item in items:
                        md += f"  - {item}\n"
                else:
                    md += "  - Non defini.\n"
        md += "\n"

        filename = f"Rapport_AEBM_{real_name.replace(' ', '_')}_{candidate_id[:6]}.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"Rapport executif genere avec succes: {filepath}")
        return filepath
