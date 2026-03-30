import os
import json
import re
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from src.schemas.state import DetailedPsychometric, TraitAnalysis


class PsychometricAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key: raise ValueError("❌ GROQ_API_KEY manquante.")
        
        # Température 0 absolue pour un diagnostic clinique
        self.llm = ChatGroq(temperature=0.0, model_name="llama-3.3-70b-versatile", groq_api_key=api_key)
        self.parser = PydanticOutputParser(pydantic_object=DetailedPsychometric)

        
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



    def _calculate_expert_score(self, candidate_data: Dict, job_target: Dict) -> Dict[str, Any]:
        """Calcul vectoriel transparent : Génère le 'ticket de caisse' des pénalités."""
        keys = [('O', 'Openness'), ('C', 'Conscientiousness'), ('E', 'Extraversion'), ('A', 'Agreeableness'), ('N', 'Neuroticism')]
        
        def get_val(data, key_tuple):
            k_short, k_long = key_tuple
            trait_data = data.get(k_short) or data.get(k_long) or {}
            if isinstance(trait_data, dict): return float(trait_data.get('score', 2.5))
            try: return float(trait_data.score)
            except: return 2.5

        def get_job_val(data, key_tuple):
            k_short, k_long = key_tuple
            val = data.get(k_short) or data.get(k_long) or 2.5
            return float(val)

        vec_c = [get_val(candidate_data, k) for k in keys]
        vec_j = [get_job_val(job_target, k) for k in keys]

        # 1. MATCH DE BASE (Cosinus)
        dot = sum(c*j for c, j in zip(vec_c, vec_j))
        mag_c = sum(c**2 for c in vec_c) ** 0.5
        mag_j = sum(j**2 for j in vec_j) ** 0.5
        similarity = dot / (mag_c * mag_j) if mag_c and mag_j else 0.0
        base_score = round(similarity * 10, 2)
        
        # 2. PÉNALITÉS DE DISTANCE & DÉTECTION DU PLUS GRAND ÉCART
        total_dist = 0.0
        biggest_gap_val = -1.0
        biggest_gap_trait = ""
        
        for i, (c, j) in enumerate(zip(vec_c, vec_j)):
            diff = abs(c - j)
            total_dist += diff
            if diff > biggest_gap_val:
                biggest_gap_val = diff
                trait_name = keys[i][1]
                trait_letter = keys[i][0]
                biggest_gap_trait = f"{trait_name} ({trait_letter}) : Cible {j}, Candidat {c} (Écart: {round(diff, 1)})"

        distance_penalty = round(total_dist * 0.4, 2)
        
        # 3. MALUS DE DISSONANCE COGNITIVE (Profil Artiste vs Job Usine)
        c_openness = vec_c[0] # Index 0 est 'O'
        j_openness = vec_j[0]
        
        cognitive_dissonance_flag = False
        dissonance_penalty = 0.0
        
        if c_openness > 4.0 and j_openness < 3.0:
            cognitive_dissonance_flag = True
            dissonance_penalty = 1.5 
            print("    DÉTECTION : Dissonance Cognitive -> Profil 'Artiste' dans un job 'Usine'.")

        # 4. CALCUL FINAL
        final = base_score - distance_penalty - dissonance_penalty
        final_score = max(0.0, min(round(final, 1), 10.0))
        
        # Le rapport complet des mathématiques Python
        return {
            "base_match_cosine": base_score,
            "total_distance_penalty": distance_penalty,
            "biggest_gap_detected": biggest_gap_trait if biggest_gap_val > 0 else "Aucun",
            "cognitive_dissonance_flag": cognitive_dissonance_flag,
            "cognitive_dissonance_penalty": dissonance_penalty,
            "final_score": final_score
        }

    def analyze_full_process(self, raw_data: Dict[str, str], job_description: str) -> Dict:
        print(" Analyse Psychométrique : Protocole Expert V4.1 (Transparence Mathématique)...")

        candidate_corpus = f"""
        [PITCH]: {raw_data.get('pitch', 'N/A')[:1500]}
        [IKIGAI]: {raw_data.get('ikigai', 'N/A')[:1500]}
        [SMART_GOALS]: {raw_data.get('smart_goals', 'N/A')[:1500]}
        [IDEAL_DAY]: {raw_data.get('ideal_day', 'N/A')[:1500]}
        """

        system_prompt = """
        Tu es un Psychologue du Travail Expert (PhD) et Profiler Linguistique travaillant pour un cabinet de Chasseurs de Têtes.
        Ta mission : Diagnostiquer le profil psychologique du candidat via une analyse HOLISTIQUE de son corpus textuel.

        ### RÈGLE ABSOLUE ANTI-HALLUCINATION
        Interdiction stricte d'attribuer des compétences de l'offre au candidat. Le candidat n'a fait QUE ce qui est écrit dans le "CANDIDATE CORPUS".

        ### ÉTAPE 1. ÉTALONNAGE DU POSTE
        Analyse le "JOB DESCRIPTION" et détermine les scores cibles (0.0 to 5.0) pour chaque trait OCEAN.
        CRITICAL: Use the exact keys "O", "C", "E", "A", "N".

        ### ÉTAPE 2. PROFILAGE DU CANDIDAT
        Lis le "CANDIDATE CORPUS" dans son INTÉGRALITÉ.
        CRITICAL: You MUST use the exact keys "O", "C", "E", "A", "N".
        
        🔍 SIGNAUX LINGUISTIQUES :
        ➡️ [O] OUVERTURE : Mots liés à la découverte, innovation.
        ➡️ [C] CONSCIENCE : Précision, chiffres, structures temporelles.
        ➡️ [E] EXTRAVERSION : "Nous", "L'équipe", réseau.
        ➡️ [A] AGRÉABILITÉ : Empathie, mentorat, soutien.
        ➡️ [N] STABILITÉ ÉMO : Gestion de la complexité, calme.

        ### CONTRAINTES DE RÉDACTION (CRITIQUES)
        - **DEPTH OF REASONING (OBLIGATOIRE)**: Pour chaque trait, tu DOIS écrire exactement 3 phrases formatées ainsi :
          "1. Observation: [...]. 2. Traduction: [...]. 3. Impact: [...]."
        - **EVIDENCE**: The `quote` MUST be an exact copy-paste in the ORIGINAL LANGUAGE.
        - **JSON SAFETY**: If you quote text inside a JSON string, you MUST use single quotes ('...') or escape double quotes (\\"). DO NOT break the JSON format.

        ### INPUTS
        [JOB DESCRIPTION] : {job_description}
        [CANDIDATE CORPUS] : {candidate_corpus}

        ### OUTPUT FORMAT (JSON ONLY)
        {format_instructions}
        """

        inputs = {
            "job_description": job_description[:4000],
            "candidate_corpus": candidate_corpus,
            "format_instructions": self.parser.get_format_instructions()
        }

        try:
            prompt = ChatPromptTemplate.from_template(system_prompt)
            chain = prompt | self.llm
            response = chain.invoke(inputs)
            
            clean_json = self._sanitize_json_output(response.content)
            result_obj = self.parser.parse(clean_json)
            final_dict = result_obj.model_dump()
            
            # Application de la Transparence Mathématique Python
            scoring_breakdown = self._calculate_expert_score(
                final_dict.get("candidate_analysis", {}), 
                final_dict.get("job_target", {})
            )
            
            # Injection des résultats dans le JSON final
            final_dict["scoring_breakdown"] = scoring_breakdown
            final_dict["job_alignment_score"] = scoring_breakdown["final_score"]
            
            return final_dict

        except Exception as e:
            print(f" Erreur Psycho Critique : {e}")
            # ON NE RENVOIE PLUS None ! On renvoie un dictionnaire de survie.
            return {
                "job_rationale": "Erreur d'analyse (Bypass)",
                "job_target": {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0},
                "candidate_analysis": {},
                "summary": "Analyse psychométrique annulée suite à une erreur de formatage de l'IA.",
                "job_alignment_score": 0.0
            }