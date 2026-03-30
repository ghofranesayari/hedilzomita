import os
import json
import re
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# --- SCHÉMAS PYDANTIC INTÉGRÉS (Pour supporter les nouveaux conseils "No-Bullshit") ---
class StarComponent(BaseModel):
    present: bool
    quality: str = Field(description="HIGH, MEDIUM, or LOW")
    reasoning: str = Field(description="OBLIGATOIRE: Rédiger exactement 2 phrases longues et détaillées (1 phrase d'Observation, 1 phrase de Critique).")
    quote: Optional[str] = Field(None, description="Citation exacte ou null si implicite.")

class StarBreakdown(BaseModel):
    Situation: StarComponent
    Task: StarComponent
    Action: StarComponent
    Result: StarComponent

class TonalAnalysis(BaseModel):
    voice_type: str = Field(description="ACTIVE (Pilote), PASSIVE (Spectateur), ou MIXED")
    agency_score: float = Field(description="0.0 à 1.0. Mesure l'agentivité (Bandura).")
    clarity_score: float = Field(description="0.0 à 1.0. Pénalisé par le jargon académique.")
    detected_jargon: List[str] = Field(description="Liste des buzzwords ou jargon lourd détectés.")

class RhetoricAnalysis(BaseModel):
    star_breakdown: StarBreakdown
    tonal_analysis: TonalAnalysis
    feedback_summary: str = Field(description="Bilan de l'impact industriel du discours.")
    impact_highlight: Optional[str] = Field(None, description="La meilleure métrique citée.")
    improvement_advice: List[str] = Field(description="3 conseils ultra-personnalisés basés sur le domaine technique précis du candidat.")

# --- L'AGENT ---
class RhetoricAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key: raise ValueError("GROQ_API_KEY manquante.")
        
        self.llm = ChatGroq(
            temperature=0.0, 
            model_name="llama-3.3-70b-versatile",
            groq_api_key=api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=RhetoricAnalysis)
    def _sanitize_json_output(self, text: str) -> str:
        text = text.strip()
        if "```" in text:
            pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
            match = re.search(pattern, text, re.DOTALL)
            text = match.group(1) if match else text.split("```")[1]
        
        start = text.find("{")
        end = text.rfind("}")
        return text[start : end + 1] if start != -1 else text
    
    def _normalize_star_keys(self, breakdown: Dict) -> Dict:
        normalized = {}
        key_map = {
            'S': 'Situation', 'Situation': 'Situation', 'situation': 'Situation',
            'T': 'Task', 'Task': 'Task', 'task': 'Task', 'Tâche': 'Task',
            'A': 'Action', 'Action': 'Action', 'action': 'Action',
            'R': 'Result', 'Result': 'Result', 'result': 'Result', 'Résultat': 'Result'
        }
        for k, v in breakdown.items():
            clean_k = k.strip()
            if clean_k in key_map:
                normalized[key_map[clean_k]] = v
            else:
                if 'S' in k and 'ituation' in k: normalized['Situation'] = v
                elif 'T' in k and 'ask' in k: normalized['Task'] = v
                elif 'A' in k and 'ction' in k: normalized['Action'] = v
                elif 'R' in k and 'esult' in k: normalized['Result'] = v
        return normalized

    def analyze_pitch(self, pitch_text: str) -> Dict:
        print("🎤 Rhetoric Agent: Inférence d'Agentivité & Audit S.T.A.R en cours...")

        system_prompt = """
        Tu es un Expert en Psycholinguistique Computationnelle et un Coach Exécutif (Tier 1).
        Ta mission est de déconstruire l'Elevator Pitch du candidat pour mesurer son véritable "Impact Industriel". 

        ### PILIER 1 : DÉCONSTRUCTION S.T.A.R.
        1. **Situation (S) & Task (T)**: Le cadre est-il posé ? (Mets MEDIUM si implicite).
        2. **Action (A)**: Valorise l'initiative réelle.
        3. **Result (R) [CRITIQUE]**: Cherche des métriques (chiffres, %, ROI).  PÉNALITÉ MAXIMALE ("LOW") si c'est du storytelling sans impact chiffré.

        ### PILIER 2 : INFÉRENCE D'AGENTIVITÉ (Théorie de Bandura)
        - Calcule le `agency_score` (0.0 à 1.0). "Je" actif = fort. "Nous/Voix passive" = faible.

        ### PILIER 3 : PSYCHOLINGUISTIQUE (Le Bruit)
        - Détecte le jargon académique excessif. Baisse le `clarity_score` s'il y a trop de "buzzwords".

        ###  PILIER 4 : CONSEILS "NO-BULLSHIT" SUR-MESURE (improvement_advice)
        Donne EXACTEMENT 3 conseils DURS, ACTIONNABLES et 100% PERSONNALISÉS basés sur les termes techniques exacts du candidat.
        -  INTERDICTION ABSOLUE D'INVENTER DES CHIFFRES (Ne dis jamais "dites que vous avez augmenté de 25%").
        - Règle : Identifie une phrase faible, et dis-lui QUEL TYPE de vraie métrique (liée à son domaine) il devrait aller chercher dans son passé pour remplacer cette phrase.
        - FORMAT EXIGÉ : "Au lieu de dire '[Citation exacte du candidat]',  précisez plutôt [Ex: le volume de cellules cultivées, le budget du projet, ou la norme ISO utilisée]."

        ### CONTRAINTES DE RÉDACTION DES JUSTIFICATIONS (REASONING)
        Pour chaque élément S.T.A.R, le champ `reasoning` DOIT contenir exactement 2 phrases :
        - Phrase 1 (Observation) : Ce que le candidat a écrit ou sous-entendu.
        - Phrase 2 (Critique) : Pourquoi cela mérite la qualité HIGH, MEDIUM ou LOW.
        
        ### FORMAT :
        TOUTES tes justifications (reasoning, feedback, advice) DOIVENT être rédigées en FRANÇAIS.
        {format_instructions}

        ### PITCH DU CANDIDAT :
        {pitch}
        """

        inputs = {
            "pitch": pitch_text[:4000],
            "format_instructions": self.parser.get_format_instructions()
        }

        try:
            prompt = ChatPromptTemplate.from_template(system_prompt)
            chain = prompt | self.llm
            response = chain.invoke(inputs)
            
            clean_json = self._sanitize_json_output(response.content)
            result_obj = self.parser.parse(clean_json)
            data = result_obj.model_dump()

            # Normalisation et Sécurité
            data['star_breakdown'] = self._normalize_star_keys(data['star_breakdown'])
            for key in ['Situation', 'Task', 'Action', 'Result']:
                if key not in data['star_breakdown']:
                    data['star_breakdown'][key] = {"present": False, "quality": "LOW", "reasoning": "Non détecté.", "quote": None}

            # CALCUL DÉTERMINISTE SOUVERAIN (Python a le dernier mot)
            score_map = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.0}
            s_score = score_map.get(data['star_breakdown']['Situation']['quality'], 0.0)
            t_score = score_map.get(data['star_breakdown']['Task']['quality'], 0.0)
            a_score = score_map.get(data['star_breakdown']['Action']['quality'], 0.0)
            r_score = score_map.get(data['star_breakdown']['Result']['quality'], 0.0)
            
            # Formule : Résultat(40%), Action(30%), Contexte S+T(30%)
            weighted_score = (s_score * 1.5) + (t_score * 1.5) + (a_score * 3.0) + (r_score * 4.0)
            
            # Bonus/Malus d'Agentivité (Bandura)
            agency = data['tonal_analysis']['agency_score']
            if agency >= 0.8: weighted_score += 0.5
            elif agency <= 0.4: weighted_score -= 1.0

            data['communication_score'] = max(0.0, min(round(weighted_score, 1), 10.0))
            
            return data

        except Exception as e:
            print(f" Erreur Rhetoric Agent : {e}")
            return None