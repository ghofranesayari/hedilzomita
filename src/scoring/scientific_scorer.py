import os
import re
from typing import Dict, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# 1. SCHÉMAS PYDANTIC (TYPE SAFETY)
# ==========================================

class ScoreDimension(BaseModel):
    score: int = Field(..., ge=1, le=5, description="Note stricte entre 1 et 5 selon la matrice.")
    label: str = Field(..., description="Le titre de la note (ex: 'Hautement Transférable').")
    proof: str = Field(..., description="Citation EXACTE issue du récit du candidat ou des preuves techniques.")
    argument: str = Field(..., description="Explication du raisonnement en FRANÇAIS.")

class ReadinessDiagnostic(BaseModel):
    transferability: ScoreDimension
    pragmatism: ScoreDimension
    complexity: ScoreDimension
    expert_summary: str = Field(..., description="Un résumé managérial implacable de 3 lignes en FRANÇAIS.")

# ==========================================
# 2. L'AGENT SCORER
# ==========================================

class ScientificScorer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key: raise ValueError("❌ GROQ_API_KEY manquante.")
        
        self.llm = ChatGroq(temperature=0.0, model_name="llama-3.3-70b-versatile", groq_api_key=api_key)
        self.parser = PydanticOutputParser(pydantic_object=ReadinessDiagnostic)

    def _sanitize_json_output(self, text: str) -> str:
        """Le bouclier anti-hallucination de format."""
        text = text.strip()
        if "```" in text:
            pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
            match = re.search(pattern, text, re.DOTALL)
            text = match.group(1) if match else text.split("```")[1]
        
        start = text.find("{")
        end = text.rfind("}")
        return text[start : end + 1] if start != -1 else text


    def calculate_readiness_cot(self, tech_analysis: List[Dict], job_description: str, candidate_narrative: str) -> Dict:
        print("🏆 Scientific Scorer: Évaluation du Readiness Level (Ruthless CTO Mode)...")

        valid_proofs = []
        for skill in tech_analysis:
            if skill.get('audit_status') == 'VALIDATED' or skill.get('status') == 'INFERRED':
                proof_text = skill.get('proof_excerpt', 'Inferred implicitly')
                valid_proofs.append(f"- {skill['skill_name']} | Preuve extraite: '{proof_text}'")

        if not valid_proofs:
            return self._generate_zero_score()

        evidence_block = "\n".join(valid_proofs)

        system_prompt = """
        Tu es un Directeur Technique (CTO) extrêmement SÉVÈRE, CYNIQUE et IMPITOYABLE.
        Tu évalues des candidats pour des postes industriels de haut niveau. 
        Ton but n'est pas d'être gentil, mais de déceler si le candidat est un théoricien ou un vrai ingénieur de production.

         RÈGLE D'OR (ANTI-BULLSHIT) :
        - Ne te laisse PAS manipuler par le discours de vente du candidat.
        - Ne donne des points QUE pour des accomplissements PASSÉS et PROUVÉS. 
        - Si le candidat dit "Je peux réduire les coûts" (promesse), c'est 0 point. S'il dit "J'ai réduit les coûts de 20%" (fait), c'est 5 points.
        - ATTENTION : Un étudiant en thèse (PhD Candidate) a par définition très peu d'expérience industrielle réelle. Il est très rare qu'il dépasse 3/5 en Pragmatisme.

        ### LA MATRICE D'ÉVALUATION (1 à 5) :

        1. TRANSFERABILITY (Académique -> Industrie)
           - 1/5: Recherche purement théorique, simulations abstraites.
           - 3/5: Prototypage, manipulation de standards (ex: ISO) en labo, Preuves de Concept (PoC).
           - 5/5: A DÉJÀ déployé des pipelines industriels, travaillé dans une vraie usine, lancé un produit certifié FDA/CE.
        
        2. PRAGMATISM (Orientation Livraison / Impact)
           - 1/5 (Explorateur): Études, analyses, publications.
           - 3/5 (Expérimentateur): Validation d'hypothèses, "Customer Discovery", lab-scale.
           - 5/5 (Bâtisseur): A DÉJÀ livré un produit sur le marché ou optimisé une vraie chaîne de production. (Interdit aux purs académiques).
        
        3. COMPLEXITY (Le Bonus "Chaos & PhD")
           - 1/5: Tâches simples sous supervision.
           - 3/5: Gestion autonome d'un projet standard.
           - 5/5: A dominé la recherche fondamentale, l'incertitude totale, ou des problèmes systémiques complexes (Généralement 5/5 pour un bon PhD).

        ### DONNÉES DU CANDIDAT :
        [VERIFIED HARD SKILLS] :
        {evidence}

        [CANDIDATE NARRATIVE (Pitch/CV)] :
        {narrative}

        [CONTEXTE DU POSTE VISÉ] :
        {job}

        ### RÈGLES DE RÉDACTION (CRITIQUES) :
        1. Tu DOIS rédiger en FRANÇAIS.
        2. Le `expert_summary` DOIT être rédigé comme un rapport de CTO tranchant, signalant immédiatement les manques (ex: "Fort en théorie, mais aucun produit livré...").

        OUTPUT FORMAT:
        {format_instructions}
        """

        prompt = ChatPromptTemplate.from_template(system_prompt)
        chain = prompt | self.llm

        try:
            response = chain.invoke({
                "evidence": evidence_block,
                "narrative": candidate_narrative[:3000],
                "job": job_description[:2000],
                "format_instructions": self.parser.get_format_instructions()
            })
            
            clean_json = self._sanitize_json_output(response.content)
            diagnostic = self.parser.parse(clean_json).model_dump()

            t_score = diagnostic['transferability']['score']
            p_score = diagnostic['pragmatism']['score']
            c_score = diagnostic['complexity']['score']

            final_score = ((t_score + p_score + c_score) / 15.0) * 10.0
            
            diagnostic['agent_id'] = "scientific_scorer_v5.2"
            diagnostic['readiness_score'] = round(final_score, 1)

            return diagnostic

        except Exception as e:
            print(f"❌ Erreur du Scientific Scorer : {e}")
            return self._generate_zero_score()

    def _generate_zero_score(self) -> Dict:
        return {
            "agent_id": "scientific_scorer_v5",
            "readiness_score": 0.0,
            "transferability": {"score": 1, "label": "N/A", "proof": "N/A", "argument": "Données insuffisantes."},
            "pragmatism": {"score": 1, "label": "N/A", "proof": "N/A", "argument": "Données insuffisantes."},
            "complexity": {"score": 1, "label": "N/A", "proof": "N/A", "argument": "Données insuffisantes."},
            "expert_summary": "Évaluation impossible : aucune compétence technique n'a passé l'audit avec succès."
        }