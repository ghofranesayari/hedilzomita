import json
import uuid
from pathlib import Path

import streamlit as st

from src.ingestion.parser import ContentParser
from src.memory.hyde import HydeGenerator
from src.memory.vector_db import VectorDBManager
from src.scoring.report import ReportGenerator
from ui.shared import cleanup_temp_dir, remove_temp_file, save_temp_file


def render_internal_mode(app_mode: str, mode_interne: str, orchestrator) -> None:
    if app_mode != mode_interne:
        return

    st.markdown("### Screening sur la base de donnees interne")

    col1, col2 = st.columns([1.2, 2])
    with col1:
        st.info("Recherche vectorielle intelligente dans votre base de candidats.")
        uploaded_job = st.file_uploader("1. Importer l'offre d'emploi (PDF)", type=["pdf"], key="int_job")
        top_k = st.slider("Nombre de profils a retenir", 1, 10, 3)

        if uploaded_job and st.button(" Lancer la recherche vectorielle ", type="primary", use_container_width=True):
            with st.spinner("Analyse de l'offre et recherche semantique..."):
                job_path = None
                try:
                    parser = ContentParser()
                    job_path = save_temp_file(uploaded_job)
                    job_text = parser.parse_pdf(Path(job_path))
                    if not parser.has_usable_text(job_text):
                        raise ValueError(
                            "Impossible d'extraire suffisamment de texte de l'offre PDF. "
                            "Utilisez un PDF texte/selectable ou un document scanne plus net."
                        )
                    st.session_state.current_job_text = job_text

                    hyde = HydeGenerator()
                    query_vec = hyde.generate_hypothetical_cvs(job_text)
                    if not query_vec or not query_vec.strip():
                        raise ValueError("La generation HyDE a retourne une requete vide.")
                    vdb = VectorDBManager("data/vector_store")

                    st.session_state.shortlist = vdb.search(query_vec, k=top_k)
                    if not st.session_state.shortlist:
                        raise RuntimeError(
                            "La recherche vectorielle n'a retourne aucun profil exploitable. "
                            "Verifiez l'extraction du PDF et les logs Streamlit si le probleme persiste."
                        )
                    st.success(f"{len(st.session_state.shortlist)} profils identifies !")
                except Exception as exc:
                    st.error(f"Erreur lors de la recherche : {exc}")
                finally:
                    if job_path:
                        remove_temp_file(job_path)
                    cleanup_temp_dir("data/temp_uploads", retention_hours=24, max_files=120)

    with col2:
        if "shortlist" in st.session_state and st.session_state.shortlist:
            st.markdown("#### Shortlist de notre preselection")

            report_gen = ReportGenerator()

            for rank, cand in enumerate(st.session_state.shortlist, 1):
                with st.container():
                    c_txt, c_btn = st.columns([3, 2])
                    with c_txt:
                        cand_id = cand["candidate_id"]
                        real_name = report_gen.get_real_name(cand_id)

                        raw_hybrid_score = cand.get("score", 0)
                        match_percent = int(raw_hybrid_score * 100)
                        st.markdown(f"**#{rank} - {real_name}**")
                        st.caption(f"`{cand_id}` | **Match Semantique : {match_percent}%**")
                        st.progress(match_percent / 100.0)
                    with c_btn:
                        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                        if st.button(f"Lancer l'Audit ", key=f"audit_int_{cand_id}", use_container_width=True):
                            with st.spinner(f"Audit Neuro-Symbolique en cours pour {real_name}..."):
                                try:
                                    with open(f"data/processed/{cand_id}.json", "r", encoding="utf-8") as file_obj:
                                        cand_data = json.load(file_obj)

                                    initial_state = {
                                        "candidate_id": cand_id,
                                        "job_description": st.session_state.current_job_text,
                                        "raw_text_data": {
                                            "cv": cand_data.get("cv_text", ""),
                                            "pitch": cand_data.get("pitch_text", ""),
                                            "clarify": cand_data.get("clarify_text", {}),
                                        },
                                        "preferences_data": cand_data.get("preferences", {}),
                                    }

                                    thread_id = f"thread_int_{cand['candidate_id']}_{uuid.uuid4().hex[:8]}"

                                    orchestrator.run_pipeline(initial_state, thread_id)
                                    final_state = orchestrator.run_pipeline(None, thread_id)

                                    report_path = report_gen.generate_markdown_report(final_state)
                                    st.session_state.current_report_path = report_path

                                    st.session_state.current_audit_result = final_state
                                    st.session_state.current_audit_id = cand["candidate_id"]
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Erreur d'audit : {exc}")
