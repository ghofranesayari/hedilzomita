import streamlit as st


def run_data_maintenance(do_ingestion: bool, do_reindex: bool) -> None:
    """Lance ingestion/reindex depuis l'UI (mode admin)."""
    if do_ingestion:
        from run_phase1_ingestion import run_ingestion

        run_ingestion()
    if do_reindex:
        from reindex import force_reindex

        force_reindex()


def render_admin_maintenance(app_mode: str, mode_interne: str) -> None:
    if app_mode != mode_interne:
        return

    st.divider()
    with st.expander("Maintenance donnees (Admin)", expanded=False):
        st.caption(
            "Utilise les chemins locaux: data/raw/batch_01 + "
            "data/raw/form_data/candidates_intake_form.xlsx"
        )
        st.caption(
            "Puis met a jour data/processed et data/vector_store "
            "(equivalent terminal: run_phase1_ingestion.py + reindex.py)."
        )
        if st.button("Lancer Ingestion + Reindexation", use_container_width=True):
            with st.spinner("Mise a jour de la base en cours..."):
                try:
                    run_data_maintenance(do_ingestion=True, do_reindex=True)
                    st.success("Mise a jour terminee: ingestion + reindexation.")
                except Exception as exc:
                    st.error(f"Echec maintenance: {exc}")

        if st.button("Lancer Reindexation seule", use_container_width=True):
            with st.spinner("Reindexation en cours..."):
                try:
                    run_data_maintenance(do_ingestion=False, do_reindex=True)
                    st.success("Reindexation terminee.")
                except Exception as exc:
                    st.error(f"Echec reindexation: {exc}")

