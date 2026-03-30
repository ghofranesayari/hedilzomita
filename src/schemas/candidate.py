from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any


class PreferenceData(BaseModel):
    """Mapping strict des colonnes Excel"""
    preferred_roles: List[str] = Field(default_factory=list, description="Q1 Checkboxes")
    top_priorities: List[str] = Field(default_factory=list, description="Q2 Ranking")
    salary_expectations: Optional[str] = Field(None, description="Q3 Numeric/Text")
    fields_of_activity: List[str] = Field(default_factory=list, description="Q4 Checkboxes")
    target_companies: Optional[str] = Field(None, description="Q5 Text")
    application_history: Optional[str] = Field(None, description="Q6 Text")
    recent_interviews: Optional[str] = Field(None, description="Q7 Text")

class CandidateDigitalTwin(BaseModel):
    """L'objet central stocké en JSON"""
    candidate_id: str = Field(..., description="UUID anonymisé (ex: CANDIDATE_885)")
    original_filename_id: str = Field(..., description="Pour retrouver le dossier source si besoin")
    
    language: str
    ingestion_date: str
    
    cv_text: str
    pitch_text: str
    # MODIFICATION ICI : clarify_text devient un Dict
    clarify_text: Dict[str, str] = Field(default_factory=dict)
    
    preferences: PreferenceData