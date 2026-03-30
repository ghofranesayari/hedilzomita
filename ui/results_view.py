import json
import os

import streamlit as st

from src.utils.visualizer import generate_radar_chart
from ui.shared import normalize_payload


def render_results() -> None:
    if "current_audit_result" not in st.session_state:
        return

    st.divider()
    res = normalize_payload(st.session_state.current_audit_result)
    cid = st.session_state.current_audit_id
    is_cv_only_candidate = cid == "SELF_AUDIT_USER"

    diag = res.get("readiness_diagnostic") or {}
    dims = diag.get("dimensions", {})

    sys_errors = res.get("system_errors", [])
    if sys_errors:
        st.warning(
            " **Alerte systeme :** Certains agents ont rencontre des erreurs et "
            f"ont utilise des valeurs par defaut : {', '.join(sys_errors)}"
        )

    st.markdown(f"##  Bilan de l'Audit : `{cid}`")

    if is_cv_only_candidate:
        _render_candidate_results(res)
    else:
        _render_internal_results(res, cid, diag, dims, is_cv_only_candidate)


def _render_candidate_results(res: dict) -> None:
    cvg = res.get("cv_global_analysis", {})
    career = res.get("role_recommendations", {})

    tab_cv_diag, tab_roles = st.tabs([" Diagnostic CV", " Postes suggeres"])

    with tab_cv_diag:
        st.markdown("### Diagnostic CV expert")
        st.write(cvg.get("expert_summary", "Diagnostic non disponible."))

        risks = cvg.get("critical_risks", [])
        if risks:
            st.markdown("#### Points a corriger")
            for risk in risks:
                st.warning(
                    f"[{risk.get('severity', 'LOW')}] {risk.get('title', 'Point')} - "
                    f"{risk.get('why_it_hurts', 'N/A')}"
                )

        actions = cvg.get("priority_actions", [])
        if actions:
            st.markdown("#### Conseils de reecriture CV")
            for action in sorted(actions, key=lambda item: item.get("priority", 99)):
                with st.expander(f"P{action.get('priority', '?')} - {action.get('action', 'Action')}"):
                    st.write(f"**Pourquoi:** {action.get('rationale', 'N/A')}")
                    if action.get("example_rewrite"):
                        st.caption(f"Exemple: {action.get('example_rewrite')}")

        st.divider()
        st.markdown("### Export")
        d1, d2 = st.columns(2)
        report_path = st.session_state.get("current_report_path")
        if report_path and os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as file_obj:
                md_content = file_obj.read()
            with d1:
                st.download_button(
                    label="Telecharger le Rapport (.md)",
                    data=md_content,
                    file_name=os.path.basename(report_path),
                    mime="text/markdown",
                    use_container_width=True,
                )
        with d2:
            st.download_button(
                label="Telecharger les Data (JSON)",
                data=json.dumps(res, indent=4, ensure_ascii=False),
                file_name=f"Data_{st.session_state.current_audit_id}.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab_roles:
        st.markdown("### Postes et domaines possibles en industrie")
        st.caption("Suggestions generees a partir de votre CV (titres + domaines + descriptions).")
        suggested = list(career.get("suggested_roles", []))
        if len(suggested) < 8:
            seen_titles = {
                str(role.get("role_title", "")).strip().lower() for role in suggested if isinstance(role, dict)
            }
            ranked_fallback = career.get("top_immediate_fit", []) + career.get("top_near_fit", [])
            for rec in ranked_fallback:
                title = str(rec.get("role_title", "")).strip()
                key = title.lower()
                if not title or key in seen_titles:
                    continue
                suggested.append(
                    {
                        "role_title": title,
                        "domain": rec.get("domain", rec.get("sector", "Industrie")),
                        "description": rec.get("role_description", "Role possible a explorer."),
                    }
                )
                seen_titles.add(key)
                if len(suggested) >= 12:
                    break
        if suggested:
            for idx, role in enumerate(suggested[:12], 1):
                with st.expander(f"{idx}. {role.get('role_title', 'Role industrie')}"):
                    st.write(f"**Domaine:** {role.get('domain', 'Industrie')}")
                    st.write(f"**Description:** {role.get('description', 'N/A')}")
        else:
            st.info("Aucune suggestion exploitable pour le moment. Renforcez le CV avec preuves de projets et impacts.")


def _render_internal_results(res: dict, cid: str, diag: dict, dims: dict, is_cv_only_candidate: bool) -> None:
    tab_resume, tab_psycho, tab_rhetoric, tab_tech, tab_logistics, tab_cv = st.tabs(
        [
            " Resume Executif",
            " Profil Psychometrique",
            " Force de Conviction",
            " Hard Skills (ADN)",
            " Faisabilite",
            " CV Industrie",
        ]
    )

    with tab_resume:
        col_a, col_b = st.columns([1, 1.5])
        with col_a:
            score_val = diag.get("score_out_of_10", 0.0)
            st.markdown(f"<h3>Readiness Score : {score_val} / 10</h3>", unsafe_allow_html=True)
            if dims and not is_cv_only_candidate:
                generate_radar_chart(dims, cid, "outputs/")
                st.image(f"outputs/{cid}_radar.png", width="stretch")
            elif is_cv_only_candidate:
                st.info("Mode candidat CV seul: graphique radar masque.")

        with col_b:
            st.markdown("###  Verdict de l'Expert IA (CTO)")
            st.markdown(
                f"<div class='result-box'>{diag.get('expert_verdict', diag.get('expert_summary', 'En attente du Scorer...'))}</div>",
                unsafe_allow_html=True,
            )

            st.markdown("### Apercu rapide")
            comm = res.get("rhetoric_analysis", {})
            log = res.get("logistics_analysis", {})
            techs = res.get("tech_analysis", [])
            cvg = res.get("cv_global_analysis", {})
            career = res.get("role_recommendations", {})
            if is_cv_only_candidate:
                st.write(f"- **Qualite CV Industrie :** {cvg.get('overall_score', 0)}/10 ({cvg.get('profile_positioning', 'N/A')})")
                st.write(f"- **Postes recommandes (fit immediat) :** {len(career.get('top_immediate_fit', []))}")
                st.write(f"- **Postes recommandes (fit proche) :** {len(career.get('top_near_fit', []))}")
            else:
                st.write(f"- **Communication :** {comm.get('communication_score', 0)}/10")
                st.write(
                    "- **Logistique :** "
                    f"{log.get('global_feasibility_score', 0)}/10 ({log.get('decision_recommendation', 'N/A')})"
                )
                st.write(
                    "- **Hard Skills valides :** "
                    f"{len([item for item in techs if item.get('audit_status') == 'VALIDATED'])} / {len(techs)}"
                )
                st.write(
                    f"- **Qualite CV Industrie :** {cvg.get('overall_score', 0)}/10 "
                    f"({cvg.get('profile_positioning', 'N/A')})"
                )

            st.divider()
            st.markdown("###  Exporter le dossier")
            d1, d2 = st.columns(2)
            report_path = st.session_state.get("current_report_path")

            if report_path and os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as file_obj:
                    md_content = file_obj.read()
                with d1:
                    st.download_button(
                        label=" Telecharger le Rapport (.md)",
                        data=md_content,
                        file_name=os.path.basename(report_path),
                        mime="text/markdown",
                        use_container_width=True,
                    )
            else:
                with d1:
                    st.error(" Rapport Markdown non genere.")

            with d2:
                st.download_button(
                    label=" Telecharger les Data (JSON)",
                    data=json.dumps(res, indent=4, ensure_ascii=False),
                    file_name=f"Data_{cid}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            st.caption(" *Astuce : Pour un PDF graphique, faites simplement Ctrl+P (Imprimer) sur cette page web.*")

    with tab_psycho:
        psycho = res.get("psychometrics", {})
        st.markdown(f"###  Score d'Alignement : {psycho.get('job_alignment_score', 0)} / 10")
        st.info(psycho.get("summary", "Resume non disponible."))

        traits = psycho.get("candidate_analysis", {})
        trait_names_map = {
            "O": "Ouverture",
            "C": "Conscience",
            "E": "Extraversion",
            "A": "Agreabilite",
            "N": "Stabilite emo.",
        }

        if traits:
            for trait_key, details in traits.items():
                full_name = trait_names_map.get(trait_key, trait_key)
                with st.expander(f"Trait : {full_name} ({trait_key}) - Score: {details.get('score', 0)}/5"):
                    raw_reasoning = details.get("reasoning", "")
                    pretty_reasoning = (
                        raw_reasoning.replace("1. Observation:", "**Observation :**")
                        .replace("2. Traduction:", "\n\n**Traduction :**")
                        .replace("3. Impact:", "\n\n**Impact :**")
                    )
                    st.markdown(pretty_reasoning)
                    st.markdown(f">  *\"{details.get('quote', '')}\"*")

    with tab_rhetoric:
        rhet = res.get("rhetoric_analysis", {})
        st.markdown(f"###  Score de Communication : {rhet.get('communication_score', 0)} / 10")
        st.success(f"**Impact majeur :** {rhet.get('impact_highlight', 'Non detecte')}")
        st.write(f"**Feedback :** {rhet.get('feedback_summary', '')}")

        star_data = rhet.get("star_breakdown", {})
        if star_data:
            st.markdown("#### Analyse S.T.A.R (Situation, Task, Action, Result)")
            for letter, details in star_data.items():
                status = "OK" if details.get("present") else "KO"
                with st.expander(f"{status} {letter} - Qualite : {details.get('quality', 'N/A')}"):
                    st.write(details.get("reasoning", ""))
                    if details.get("quote"):
                        st.caption(f"\"{details.get('quote')}\"")
        advice_list = rhet.get("improvement_advice", [])
        if advice_list:
            st.markdown("#### Conseils de reecriture (amelioration du pitch)")
            for advice in advice_list:
                st.warning(f" {advice}")

    with tab_tech:
        st.markdown("### Evaluation de maturite (Readiness)")
        cto_details = diag.get("tech_details", {})

        if cto_details:
            for dim_key, icon in [("transferability", ""), ("pragmatism", ""), ("complexity", "")]:
                dim = cto_details.get(dim_key, {})
                if dim:
                    with st.container():
                        st.markdown(f"#### {icon} {dim_key.upper()} : {dim.get('score', 0)}/5 - *{dim.get('label', '')}*")
                        st.write(f"**Justification :** {dim.get('argument', 'N/A')}")
                        st.info(f" **Preuve du CTO :** *\"{dim.get('proof', 'N/A')}\"*")
            st.divider()
        else:
            st.warning("Evaluation de maturite non disponible.")

        st.markdown("### Inventaire des competences valides")
        techs = res.get("tech_analysis", [])
        if techs:
            for skill in techs:
                status = skill.get("audit_status", "PENDING")
                icon = "OK" if status == "VALIDATED" else "KO" if status == "REJECTED" else "WARN"
                with st.expander(f"{icon} {skill.get('skill_name', 'Inconnu')} ({skill.get('category', '')})"):
                    st.write(f"**Recherche Initiale :** {skill.get('status', '')}")
                    st.write(f"**Source :** {skill.get('source', '')}")
                    st.write(f"**Commentaire Audit :** {skill.get('audit_comment', 'Aucun commentaire.')}")
                    if skill.get("proof_excerpt"):
                        st.markdown(f">  **Preuve extraite du CV :**\n> *\"{skill.get('proof_excerpt')}\"*")
        else:
            st.warning("Aucune competence technique extraite.")

    with tab_logistics:
        log = res.get("logistics_analysis", {})
        st.markdown(f"###  Score de faisabilite : {log.get('global_feasibility_score', 0)} / 10")
        st.write(f"**Recommandation :** {log.get('decision_recommendation', 'N/A')}")

        flags = log.get("flags", [])
        if flags:
            for flag in flags:
                icon = (
                    "OK"
                    if flag["status"] == "MATCH"
                    else "BONUS"
                    if flag["status"] == "BONUS"
                    else "WARN"
                    if flag["status"] in ["WARNING", "INFO"]
                    else "KO"
                )
                st.write(f"- {icon} **[{flag.get('category', '')}]** : {flag.get('details', '')}")

    with tab_cv:
        cvg = res.get("cv_global_analysis", {})
        st.markdown(f"###  Score CV Industrie : {cvg.get('overall_score', 0)} / 10")
        st.write(f"**Positionnement :** {cvg.get('profile_positioning', 'N/A')}")
        st.write(f"**Confiance :** {cvg.get('confidence', 0)}")

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("#### Rubric")
            st.write(f"- **Industry relevance :** {cvg.get('industry_relevance', 0)}/10")
            st.write(f"- **Business impact :** {cvg.get('business_impact', 0)}/10")
            st.write(f"- **Transferability narrative :** {cvg.get('transferability_narrative', 0)}/10")
        with col_r:
            st.markdown("#### Rubric (suite)")
            st.write(f"- **Brevity & focus :** {cvg.get('brevity_focus', 0)}/10")
            st.write(f"- **Publication calibration :** {cvg.get('publication_calibration', 0)}/10")
            st.write(f"- **Evidence quality :** {cvg.get('evidence_quality', 0)}/10")

        style_flags = cvg.get("cv_style_flags", {})
        if style_flags:
            st.markdown("#### Signaux de style detectes")
            st.write(f"- **Densite publications elevee :** {style_flags.get('high_publication_density', False)}")
            st.write(f"- **Densite metriques business faible :** {style_flags.get('low_business_metric_density', False)}")
            st.write(
                "- **Compteurs :** publications="
                f"{style_flags.get('publication_signal_count', 0)}, business_metrics="
                f"{style_flags.get('business_metric_signal_count', 0)}"
            )

        risks = cvg.get("critical_risks", [])
        if risks:
            st.markdown("#### Risques critiques")
            for risk in risks:
                severity = risk.get("severity", "LOW")
                if severity == "HIGH":
                    st.error(
                        f"[{severity}] {risk.get('title', 'Risque')}\n\n"
                        f"Preuve: \"{risk.get('evidence', 'N/A')}\"\n\n"
                        f"Impact: {risk.get('why_it_hurts', 'N/A')}"
                    )
                elif severity == "MEDIUM":
                    st.warning(
                        f"[{severity}] {risk.get('title', 'Risque')}\n\n"
                        f"Preuve: \"{risk.get('evidence', 'N/A')}\"\n\n"
                        f"Impact: {risk.get('why_it_hurts', 'N/A')}"
                    )
                else:
                    st.info(
                        f"[{severity}] {risk.get('title', 'Risque')}\n\n"
                        f"Preuve: \"{risk.get('evidence', 'N/A')}\"\n\n"
                        f"Impact: {risk.get('why_it_hurts', 'N/A')}"
                    )

        actions = cvg.get("priority_actions", [])
        if actions:
            st.markdown("#### Plan de correction priorise")
            for action in sorted(actions, key=lambda item: item.get("priority", 99)):
                with st.expander(f"P{action.get('priority', '?')} - {action.get('action', 'Action')}"):
                    st.write(f"**Pourquoi :** {action.get('rationale', 'N/A')}")
                    if action.get("example_rewrite"):
                        st.caption(f"Exemple : {action.get('example_rewrite')}")

