import streamlit as st
import os

# --- IMPORTS BACKEND SOUVERAIN ---
from src.memory.graph_store import GraphStore
from src.orchestration.graph import AEBMGraphOrchestrator
from ui.admin_maintenance import render_admin_maintenance
from ui.candidate_mode import render_candidate_mode
from ui.internal_mode import render_internal_mode
from ui.results_view import render_results
from ui.shared import cleanup_temp_dir

# --- 1. CONFIGURATION UI ---
st.set_page_config(
    page_title="AEBM V5 | The Sovereign", 
    page_icon="ðŸ”¬", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1.b MAINTENANCE TEMPORAIRE AUTOMATIQUE ---
# Nettoie silencieusement les fichiers temporaires anciens pour eviter accumulation.
cleanup_temp_dir("data/temp_uploads", retention_hours=24, max_files=120)
cleanup_temp_dir("data/temp_b2b", retention_hours=24, max_files=50)



# --- 2. CSS PREMIUM LIGHT MODE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');


    :root {
        --bg-main: #F4F7FB;
        --bg-soft: #EEF4FA;
        --surface: rgba(255, 255, 255, 0.88);
        --surface-strong: rgba(255, 255, 255, 0.96);
        --border: rgba(20, 35, 63, 0.08);
        --border-strong: rgba(20, 35, 63, 0.12);
        --text-main: #16233F;
        --text-soft: #607089;
        --blue: #1668E3;
        --blue-soft: #EAF2FF;
        --orange: #FF7A1A;
        --orange-strong: #F25C05;
        --orange-soft: #FFF2E8;
        --success: #16A34A;
        --warning: #F59E0B;
        --danger: #DC2626;
        --radius-xl: 24px;
        --radius-lg: 18px;
        --radius-md: 14px;
        --shadow-sm: 0 6px 18px rgba(15, 23, 42, 0.04);
        --shadow-md: 0 12px 30px rgba(15, 23, 42, 0.06);
        --shadow-lg: 0 20px 45px rgba(22, 104, 227, 0.10);
        --shadow-orange: 0 14px 35px rgba(255, 122, 26, 0.18);
    }


    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }


    /* ===== APP GLOBALE ===== */
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(22, 104, 227, 0.08) 0%, transparent 24%),
            radial-gradient(circle at top right, rgba(255, 122, 26, 0.10) 0%, transparent 22%),
            linear-gradient(180deg, #F8FBFF 0%, #F4F7FB 55%, #EEF3F9 100%);
        color: var(--text-main);
    }


    [data-testid="stHeader"] {
        background: rgba(255,255,255,0) !important;
    }


    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 2.2rem !important;
        max-width: 1450px;
    }


    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,253,0.96) 100%);
        border-right: 1px solid var(--border);
        box-shadow: 8px 0 28px rgba(15, 23, 42, 0.04);
    }


    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.1rem;
    }


    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {
        color: var(--text-main) !important;
    }


    /* ===== TYPO ===== */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-main) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }


    p, span, label, div {
        color: var(--text-main);
    }


    .stMarkdown p {
        color: var(--text-soft);
        line-height: 1.65;
    }


    /* ===== HERO ===== */
    .hero-header {
        position: relative;
        overflow: hidden;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(250,252,255,0.98) 100%);
        border: 1px solid var(--border);
        border-radius: 28px;
        padding: 2.2rem 2.1rem;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-md);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }


    .hero-header::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            radial-gradient(circle at 12% 20%, rgba(22,104,227,0.13), transparent 22%),
            radial-gradient(circle at 88% 18%, rgba(255,122,26,0.16), transparent 20%);
        pointer-events: none;
    }


    .hero-header::after {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        width: 7px;
        height: 100%;
        background: linear-gradient(180deg, var(--orange) 0%, var(--blue) 100%);
        border-radius: 28px 0 0 28px;
    }


    .hero-header h1 {
        font-weight: 800;
        margin: 0 0 10px 0;
        font-size: 2.35rem;
        line-height: 1.08;
        color: var(--text-main) !important;
        position: relative;
        z-index: 1;
    }


    .hero-tag {
        background: linear-gradient(135deg, var(--orange-soft) 0%, #FFF8F2 100%);
        color: var(--orange-strong) !important;
        padding: 6px 14px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        display: inline-block;
        width: fit-content;
        margin-bottom: 12px;
        border: 1px solid rgba(255, 122, 26, 0.18);
        box-shadow: 0 8px 18px rgba(255, 122, 26, 0.10);
        position: relative;
        z-index: 1;
    }


    .hero-header p {
        color: var(--text-soft) !important;
        font-size: 1.05rem;
        margin: 0;
        max-width: 900px;
        position: relative;
        z-index: 1;
    }


    /* ===== CARTES / CONTAINERS ===== */
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
        background: linear-gradient(180deg, rgba(255,255,255,0.88) 0%, rgba(255,255,255,0.97) 100%);
        border-radius: 20px;
        padding: 1.35rem;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        transition: all 0.25s ease;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }


    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"]:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        border-color: rgba(22, 104, 227, 0.14);
    }


    /* ===== INPUTS ===== */
    .stTextArea textarea,
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTimeInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.94) !important;
        color: var(--text-main) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 14px !important;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.02);
    }


    .stTextArea textarea:focus,
    .stTextInput input:focus,
    .stNumberInput input:focus {
        border-color: rgba(22, 104, 227, 0.35) !important;
        box-shadow: 0 0 0 4px rgba(22, 104, 227, 0.10) !important;
    }


    .stTextArea textarea {
        line-height: 1.6 !important;
    }


    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        background: linear-gradient(180deg, rgba(255,255,255,0.88) 0%, rgba(250,252,255,0.96) 100%);
        border: 1.5px dashed rgba(22, 104, 227, 0.22);
        border-radius: 18px;
        padding: 0.8rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
    }


    [data-testid="stFileUploader"]:hover {
        border-color: rgba(255, 122, 26, 0.35);
        background: linear-gradient(180deg, #FFFFFF 0%, #FFF9F4 100%);
    }


    /* ===== SLIDER ===== */
    .stSlider [data-baseweb="slider"] > div > div {
        background: linear-gradient(90deg, var(--blue) 0%, var(--orange) 100%) !important;
    }


    /* ===== BOUTONS ===== */
    .stButton > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        min-height: 2.85rem;
        transition: all 0.22s ease !important;
    }


    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FF8A2A 0%, #F25C05 52%, #1668E3 140%);
        color: white !important;
        border: none !important;
        box-shadow: var(--shadow-orange);
    }


    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 18px 30px rgba(242, 92, 5, 0.22);
        filter: brightness(1.02);
    }


    .stButton > button[kind="primary"] * {
        color: white !important;
    }


    .stButton > button[kind="secondary"] {
        background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(248,250,253,0.98) 100%);
        color: var(--text-main) !important;
        border: 1px solid var(--border-strong) !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
    }


    .stButton > button[kind="secondary"]:hover {
        color: var(--blue) !important;
        border-color: rgba(22, 104, 227, 0.24) !important;
        transform: translateY(-1px);
    }


    /* ===== RADIO ===== */
    div[role="radiogroup"] {
        background: linear-gradient(180deg, rgba(248,250,253,0.95) 0%, rgba(255,255,255,0.98) 100%);
        padding: 10px;
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.85);
    }


    div[role="radiogroup"] label {
        border-radius: 12px;
        padding: 0.55rem 0.7rem;
        transition: all 0.18s ease;
        margin-bottom: 0.25rem;
    }


    div[role="radiogroup"] label:hover {
        background: rgba(22, 104, 227, 0.06);
    }


    div[role="radiogroup"] label[data-selected="true"] {
        background: linear-gradient(135deg, rgba(22,104,227,0.10) 0%, rgba(255,122,26,0.10) 100%);
        border: 1px solid rgba(22,104,227,0.14);
    }


    /* ===== ALERTES ===== */
    [data-testid="stAlert"] {
        border-radius: 16px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }


    [data-testid="stAlert"][kind="info"] {
        background: linear-gradient(135deg, #EFF6FF 0%, #F8FBFF 100%) !important;
        border-color: rgba(22, 104, 227, 0.14) !important;
        color: #0F4FCB !important;
    }


    [data-testid="stAlert"][kind="success"] {
        background: linear-gradient(135deg, #ECFDF3 0%, #F8FFFB 100%) !important;
        border-color: rgba(22, 163, 74, 0.15) !important;
    }


    [data-testid="stAlert"][kind="warning"] {
        background: linear-gradient(135deg, #FFF8EB 0%, #FFFCF5 100%) !important;
        border-color: rgba(245, 158, 11, 0.18) !important;
    }


    [data-testid="stAlert"][kind="error"] {
        background: linear-gradient(135deg, #FFF1F2 0%, #FFF8F8 100%) !important;
        border-color: rgba(220, 38, 38, 0.16) !important;
    }


    /* ===== RESULT BOX ===== */
    .result-box {
        background: linear-gradient(135deg, #F7FAFF 0%, #EEF5FF 100%);
        border-left: 5px solid var(--blue);
        padding: 16px 18px;
        border-radius: 14px;
        margin-bottom: 15px;
        color: var(--text-main) !important;
        box-shadow: 0 10px 24px rgba(22, 104, 227, 0.08);
        border-top: 1px solid rgba(22, 104, 227, 0.08);
        border-right: 1px solid rgba(22, 104, 227, 0.08);
        border-bottom: 1px solid rgba(22, 104, 227, 0.08);
    }


    /* ===== STATUS / SPINNER ===== */
    [data-testid="stStatusWidget"] {
        border-radius: 18px !important;
        border: 1px solid var(--border) !important;
        background: linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(250,252,255,0.98) 100%) !important;
        box-shadow: var(--shadow-sm);
    }


    [data-testid="stSpinner"] > div {
        border-top-color: var(--orange) !important;
    }


    /* ===== DOWNLOAD BUTTON ===== */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1668E3 0%, #0F4FCB 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        box-shadow: var(--shadow-lg);
    }


    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        filter: brightness(1.03);
    }


    .stDownloadButton > button * {
        color: white !important;
    }


    /* ===== IMAGES ===== */
    img {
        border-radius: 16px;
    }


    /* ===== DIVIDER / CAPTION ===== */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(
            90deg,
            rgba(22,104,227,0),
            rgba(22,104,227,0.16),
            rgba(255,122,26,0.16),
            rgba(255,122,26,0)
        );
    }


    .stCaption, .stCaption p {
        color: #7B8799 !important;
        font-weight: 500;
    }


    /* ===== TOAST ===== */
    [data-testid="stToast"] {
        border-radius: 14px !important;
        background: rgba(255,255,255,0.96) !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow-md);
    }


    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }


    ::-webkit-scrollbar-track {
        background: #EEF3F9;
        border-radius: 10px;
    }


    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, rgba(22,104,227,0.45) 0%, rgba(255,122,26,0.45) 100%);
        border-radius: 10px;
    }


    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, rgba(22,104,227,0.70) 0%, rgba(255,122,26,0.70) 100%);
    }
            
    
    [data-testid="stExpander"] details {
        border: 1px solid var(--border-strong) !important;
        border-radius: 12px !important;
        background-color: #FFFFFF !important;
    }
    
    [data-testid="stExpander"] summary {
        background-color: var(--bg-soft) !important;
        color: var(--text-main) !important;
        border-radius: 12px !important;
        padding: 0.5rem 1rem !important;
    }
    
    [data-testid="stExpander"] summary:hover {
        background-color: var(--blue-soft) !important;
    }
    
    [data-testid="stExpander"] p {
        color: var(--text-main) !important;
    }


    /* ===== RESPONSIVE ===== */
    @media (max-width: 900px) {
        .hero-header {
            padding: 1.6rem 1.2rem;
            border-radius: 22px;
        }


        .hero-header h1 {
            font-size: 1.8rem !important;
        }


        div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# --- 3. INITIALISATION SéCURISÉE DE NEO4J ---
def init_system(neo4j_uri: str, neo4j_user: str, neo4j_mode: str):
    print("Tentative de connexion à Neo4j...")
    try:
        gs = GraphStore()
        gs.setup_database()
        gs.initialize_ontology()
        gs.close()
        return "SUCCESS"
    except Exception as e:
        return str(e)

_db_sig = (
    os.getenv("NEO4J_URI", ""),
    os.getenv("NEO4J_USER", ""),
    os.getenv("AEBM_NEO4J_MODE", ""),
)
if st.session_state.get("_db_init_sig") != _db_sig or st.session_state.get("_db_status") != "SUCCESS":
    st.session_state["_db_status"] = init_system(*_db_sig)
    st.session_state["_db_init_sig"] = _db_sig

db_status = st.session_state.get("_db_status", "UNKNOWN")
if db_status != "SUCCESS":
    st.error("**ERREUR CRITIQUE : IMPOSSIBLE DE JOINDRE NEO4J**")
    neo4j_uri = (os.getenv("NEO4J_URI", "") or "").strip().lower()
    if neo4j_uri.startswith("neo4j+s://"):
        st.warning(
            "Connexion Neo4j Cloud (AuraDB) échouée. "
            "Vérifiez NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD dans .env."
        )
    else:
        st.warning("Le Graphe de Connaissance (Neo4j) est éteint. Lancez votre conteneur Docker.")
    with st.expander("Détails Techniques"):
        st.code(db_status)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = AEBMGraphOrchestrator()

# --- 4. SIDEBAR & NAVIGATION ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #FF6B00 !important;'>The 2nd Lab</h2>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### Navigation")
    mode_interne = "Mode Interne (Base Existante)"
    mode_candidat = "Mode Candidat"
    app_mode = st.radio(
        "Mode d'Utilisation",
        [mode_interne, mode_candidat],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("Réinitialiser l'affichage"):
        st.session_state.pop("current_audit_result", None)
        st.session_state.pop("shortlist", None)
        st.rerun()

    render_admin_maintenance(app_mode, mode_interne)

# --- 5. HEADER PRINCIPAL ---
st.markdown("""
<div class="hero-header">
    <div class="hero-tag">Notre outil d'aide à la décision</div>
    <h1>Plateforme d'audit agentique multidimensionnel</h1>
    <p>Évaluation multidimensionnelle pour talents hautement qualifiés (PhD & Experts).</p>
</div>
""", unsafe_allow_html=True)

render_internal_mode(app_mode, mode_interne, st.session_state.orchestrator)
render_candidate_mode(app_mode, mode_candidat, st.session_state.orchestrator)
render_results()
