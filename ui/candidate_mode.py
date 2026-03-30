import uuid
from pathlib import Path

import streamlit as st

from src.ingestion.parser import ContentParser
from src.scoring.report import ReportGenerator
from ui.shared import cleanup_temp_dir, remove_temp_file, save_temp_file


def render_candidate_mode(app_mode: str, mode_candidat: str, orchestrator) -> None:
    if app_mode not in (mode_candidat, "Mode Candidat (CV seul)"):
        return

    st.markdown("### Evaluation candidat (CV seul)")
    st.info(
        "Chargez uniquement votre CV. Le systeme produit une evaluation globale, "
        "des conseils experts, et des postes recommandes en industrie."
    )

    col1, col2 = st.columns([1.15, 1])
    with col1:
        up_cv = st.file_uploader("CV (PDF)", type=["pdf"], key="c_cv_only")
        st.caption("Entree obligatoire: votre CV uniquement.")
    with col2:
        target_sectors = st.multiselect(
            "Secteurs preferes (optionnel)",
            ["biotech", "medtech", "pharma", "qa_ra", "data", "manufacturing", "product", "consulting", "startup"],
            default=[],
        )
        target_domain_text = st.text_input(
            "Domaine vise (libre, optionnel)",
            placeholder="Ex: systemes embarques, robotique, IoT, automobile, aerospace",
        )

    if st.button("Generer mon diagnostic CV", type="primary", use_container_width=True):
        if not up_cv:
            st.error("Veuillez uploader un CV PDF.")
            return

        with st.spinner("Analyse CV en cours..."):
            cv_temp_path = None
            try:
                parser = ContentParser()
                cv_temp_path = save_temp_file(up_cv)
                cv_txt = parser.parse_pdf(Path(cv_temp_path))

                pseudo_job_desc = (
                    "Evaluation de transition PhD/Postdoc vers industrie. "
                    f"Secteurs cibles: {', '.join(target_sectors) if target_sectors else 'general'}. "
                    f"Domaine libre: {target_domain_text if target_domain_text else 'non specifie'}. "
                    "Objectif: mesurer la transferabilite, l'impact business, et recommander des postes realistes."
                )

                cand_id = "SELF_AUDIT_USER"
                initial_state = {
                    "candidate_id": cand_id,
                    "job_description": pseudo_job_desc,
                    "raw_text_data": {
                        "cv": cv_txt,
                        "pitch": "",
                        "clarify": {},
                    },
                    "preferences_data": {
                        "target_sectors": target_sectors,
                        "target_domain_text": target_domain_text,
                        "recommendation_mode": "open_world",
                    },
                }

                thread_id = f"thread_cv_{uuid.uuid4().hex[:8]}"
                orchestrator.run_pipeline(initial_state, thread_id)
                final_state = orchestrator.run_pipeline(None, thread_id)

                report_gen = ReportGenerator()
                report_path = report_gen.generate_markdown_report(final_state)
                st.session_state.current_report_path = report_path
                st.session_state.current_audit_result = final_state
                st.session_state.current_audit_id = cand_id
                st.rerun()
            except Exception as exc:
                st.error(f"Erreur lors de l'analyse: {exc}")
            finally:
                if cv_temp_path:
                    remove_temp_file(cv_temp_path)
                cleanup_temp_dir("data/temp_uploads", retention_hours=24, max_files=80)
