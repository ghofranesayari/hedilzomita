from typing import Dict, List, Optional, Literal, TypedDict, Annotated, Any
from pydantic import BaseModel, Field
import operator

# ==========================================
# 1. ÉTAT GLOBAL DU GRAPHE (LA MÉMOIRE STRICTE V5)
# ==========================================
# Note du CTO: total=False permet au graphe de démarrer même si toutes les clés 
# ne sont pas remplies dès le départ.
class MatchingState(TypedDict, total=False):
    """La mémoire partagée du pipeline LangGraph."""
    # --- PHASE 1 : Inputs Statiques ---
    candidate_id: str
    job_description: str
    raw_text_data: Dict[str, Any] 
    preferences_data: Dict[str, Any] 
    
    # --- PHASE 2 : Données Nettoyées ---
    managed_context: Dict[str, str] 
    job_metadata: Dict[str, Any]    
    job_dna: Dict[str, List[str]]    
    
    # --- PHASE 3 : Boucle Hard Skills (Job DNA) ---
    tech_analysis: List[Dict] 
    audit_feedback: str # Plus besoin d'Annotated ici si on écrase la string à chaque boucle
    retry_count: int 
    last_verdict: str 
    needs_human_review: bool 
    
    # --- PHASE 4 : Le Fan-Out (Soft Skills & Logistics) ---
    # CORRECTION CRITIQUE : Déclaration des clés individuelles.
    # Plus besoin de reducer (deep_update), chaque agent gère sa propre clé !
    psychometrics: dict
    rhetoric_analysis: dict
    logistics_analysis: dict
    cv_global_analysis: dict
    role_recommendations: dict
    
    # --- PHASE 5 : Outputs Finaux ---
    readiness_diagnostic: Dict[str, Any] 
    final_readiness_score: float
    system_errors: Annotated[List[str], operator.add] 

# ==========================================
# 2. SCHÉMAS PYDANTIC (PHASE 3: JOB DNA)
# ==========================================
class SkillProof(BaseModel):
    category: Literal["ACADEMIC", "TOOL", "RESPONSIBILITY", "STANDARD"] = Field(...)
    skill_name: str = Field(..., description="L'exigence spécifique.")
    status: Literal["FOUND", "MISSING", "INFERRED", "PARTIALLY_FOUND"] = Field(...)
    proof_excerpt: Optional[str] = Field(None, description="Citation exacte du CV")
    source: Literal["CV_TEXT", "GRAPH_INFERENCE", "GRAPH_SYNONYM_SEARCH", "UNKNOWN"]
    audit_status: Literal["PENDING", "VALIDATED", "REJECTED", "UNVERIFIED"] = "PENDING"
    audit_comment: Optional[str] = None

# ==========================================
# 3. SCHÉMAS PYDANTIC (PHASE 4: FAN-OUT)
# ==========================================

class TraitAnalysis(BaseModel):
    score: float = Field(..., ge=0.0, le=5.0)
    reasoning: str = Field(
        ..., 
        description="EXIGENCE ABSOLUE: Rédiger OBLIGATOIREMENT 3 phrases longues et détaillées. "
                    "Phrase 1 doit commencer par '1. Observation :'. "
                    "Phrase 2 doit commencer par '2. Traduction :'. "
                    "Phrase 3 doit commencer par '3. Impact :'."
    )
    quote: str = Field(..., description="Citation exacte tirée du texte, obligatoire.")

class DetailedPsychometric(BaseModel):
    job_rationale: str = Field(..., description="Justification détaillée du profil psychologique requis pour le poste.")
    job_target: Dict[str, float] = Field(...)
    candidate_analysis: Dict[str, TraitAnalysis] = Field(...)
    summary: str = Field(..., description="Un paragraphe complet résumant le fit psychologique.")
    job_alignment_score: float = Field(default=0.0)

class StarMetric(BaseModel):
    present: bool = Field(...)
    quality: Literal["LOW", "MEDIUM", "HIGH"] = Field(...)
    reasoning: str = Field(
        ..., 
        description="OBLIGATOIRE: Rédiger exactement 2 phrases longues et détaillées. "
                    "La phrase 1 décrit l'observation (ce que le candidat a écrit). "
                    "La phrase 2 justifie sévèrement la qualité HIGH/MEDIUM/LOW."
    )
    quote: Optional[str] = Field(None, description="Citation exacte ou null si totalement absent.")

class TonalMetric(BaseModel):
    voice_type: Literal["ACTIVE", "PASSIVE", "MIXED"] = Field(...)
    clarity_score: float = Field(...)
    persuasion_score: float = Field(...)
    detected_jargon: List[str] = Field(default_factory=list)

class RhetoricAnalysis(BaseModel):
    star_breakdown: Dict[str, StarMetric] = Field(...)
    tonal_analysis: TonalMetric
    communication_score: float = Field(...)
    feedback_summary: str = Field(..., description="Un paragraphe complet (3-4 phrases) résumant l'impact du discours.")
    impact_highlight: Optional[str] = Field(None)
    improvement_advice: List[str] = Field(
        default_factory=list, 
        description="Exactement 3 conseils LONGS et ultra-personnalisés. Format exigé: 'Au lieu de dire X, précisez Y'."
    )


# ==========================================
# 4. SCHÉMAS PYDANTIC (PHASE 5: SCORER)
# ==========================================
class ScoreDimension(BaseModel):
    score: int = Field(..., ge=1, le=5)
    label: str = Field(...)
    proof: str = Field(...)
    argument: str = Field(...)

class ReadinessDiagnostic(BaseModel):
    transferability: ScoreDimension
    pragmatism: ScoreDimension
    complexity: ScoreDimension
    expert_summary: str = Field(...)
