import os
import json
import re
from typing import List, Dict 
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from src.schemas.state import SkillProof
from src.memory.graph_store import GraphStore

# =========================================================
# --- NOUVEAUX SCHÉMAS POUR L'EXTRACTION D'ADN (REQUIS !) ---
# =========================================================
class JobDNA(BaseModel):
    ACADEMIC: List[str] = Field(description="Diplômes et domaines d'études exigés (ex: 'PhD in Biomaterials', 'M.Sc in Computer Science'). Max 2.")
    TOOL: List[str] = Field(description="Logiciels, langages de programmation, ou équipements physiques (ex: 'SolidWorks', 'Python', 'Flow Cytometry'). Max 5.")
    STANDARD: List[str] = Field(description="Normes réglementaires ou méthodologies (ex: 'ISO 13485', 'GMP', 'Agile/Scrum'). Max 3.")
    RESPONSIBILITY: List[str] = Field(description="Tâches ou responsabilités critiques du poste (ex: 'Lead cross-functional teams', 'Regulatory submissions'). Max 3.")

class BridgeExtraction(BaseModel):
    skills: List[SkillProof]

# =========================================================

class BridgeAgent:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0.0, 
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.graph = GraphStore()
        self.dna_parser = PydanticOutputParser(pydantic_object=JobDNA)
        self.proof_parser = PydanticOutputParser(pydantic_object=BridgeExtraction)

    def _sanitize_json_output(self, text: str) -> str:
        text = text.strip()
        if "```" in text:
            pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
            match = re.search(pattern, text, re.DOTALL)
            text = match.group(1) if match else text.split("```")[1]
        
        start = text.find("{")
        end = text.rfind("}")
        return text[start : end + 1] if start != -1 else text

    def extract_job_dna(self, job_description: str) -> Dict[str, List[str]]:
        print("🧬 Bridge Agent: Step 1 - Séquençage de l'ADN du poste...")
        
        prompt = ChatPromptTemplate.from_template("""
        You are an elite, domain-agnostic Technical Recruiter.
        Extract the Job DNA (Core requirements) from this Job Description and categorize them perfectly.

        CRITICAL RULES:
        1. ATOMIC PRECISION: Break down complex categories. Do not write "3D Modeling (SolidWorks, AutoCAD)". Write "SolidWorks", "AutoCAD" in the TOOL category.
        2. EXCLUDE TRIVIALS: Strictly exclude basic IT (MS Office, Word) and soft skills (Communication, Motivation).
        3. BE SPECIFIC: For RESPONSIBILITY, extract concrete technical duties, not vague platitudes.

        JOB DESCRIPTION:
        {job_description}

        OUTPUT FORMAT:
        {format_instructions}
        """)
        
        chain = prompt | self.llm
        try:
            response = chain.invoke({
                "job_description": job_description,
                "format_instructions": self.dna_parser.get_format_instructions()
            })
            clean_json = self._sanitize_json_output(response.content)
            dna = self.dna_parser.parse(clean_json)
            return dna.model_dump()
        except Exception as e:
            print(f" Erreur Extraction DNA: {e}")
            return {"ACADEMIC": [], "TOOL": [], "STANDARD": [], "RESPONSIBILITY": []}

    def analyze(self, cv_text: str, job_dna: Dict[str, List[str]], feedback: str = "") -> List[Dict]:
        print(f" Bridge Agent: Step 2 - Fouille Sémantique de l'ADN...")

        STOPLIST = ["ms office", "word", "excel", "powerpoint", "windows", "email", "internet", "outlook", "microsoft office", "ms suite"]

        feedback_instruction = ""
        if feedback:
            print(f"    RETRY ACTIVÉ avec feedback de l'Auditeur.")
            feedback_instruction = f"""
            ###  CRITICAL FEEDBACK FROM PREVIOUS AUDIT
            "{feedback}"
            YOUR MISSION: Find better, undeniable physical evidence. If none exist, mark as 'MISSING'.
            """

        system_prompt = """
        You are a Forensic CV Auditor. Find concrete proof in the CV for the requested Job DNA.

        {feedback_instruction}

        ### INPUTS
        - JOB DNA: {job_dna}
        - CV Content: (Below)

        ###  FORENSIC REASONING RULES:
        1. **For TOOL & STANDARD:** Search for the exact word or its direct technical implication. CRITICAL: You MUST extract the exact sentence (10-25 words) from the CV and put it in the `proof_excerpt` field. DO NOT LEAVE IT NULL if status is FOUND.
        2. **For ACADEMIC:** Degrees are often written differently. "M.Ing en Génie" matches "Master in Engineering". Extract the degree line.
        3. **For RESPONSIBILITY:** Look at the 'Experience' section. Find a sentence describing an action that semantically proves the candidate can do this task.
        4. **STRICT HONESTY:** If there is no concrete proof, status MUST be 'MISSING' and `proof_excerpt` MUST be `null`. DO NOT HALLUCINATE.

        ### OUTPUT FORMAT (JSON ONLY)
        {format_instructions}

        ### CANDIDATE CV:
        {cv_text}
        """

        prompt = ChatPromptTemplate.from_template(system_prompt)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "job_dna": json.dumps(job_dna),
                "cv_text": cv_text, 
                "feedback_instruction": feedback_instruction,
                "format_instructions": self.proof_parser.get_format_instructions()
            })
            clean_json = self._sanitize_json_output(response.content)
            result = self.proof_parser.parse(clean_json)
            skills_found = result.skills
        except Exception as e:
            print(f" Bridge LLM Error: {e}")
            return []

        final_skills = []
        cv_lower = cv_text.lower()

        for skill in skills_found:
            skill_dict = skill.model_dump()
            s_name_clean = re.sub(r'[^a-z0-9]', ' ', skill.skill_name.lower()).strip()
            
            # Filtre de sécurité basique pour les Outils
            if skill_dict["category"] == "TOOL" and (any(ban in s_name_clean for ban in STOPLIST) or any(ban == skill.skill_name.lower() for ban in STOPLIST)):
                print(f" 🗑️ Ignoré (Outil Trivial bloqué) : {skill.skill_name}")
                continue
            
            # 🛡️ LE FILET DE SÉCURITÉ NEO4J (Uniquement pour TOOL et STANDARD)
            if skill_dict["status"] == "MISSING" and skill_dict["category"] in ["TOOL", "STANDARD"]:
                synonyms = self.graph.get_synonyms_and_related(skill.skill_name)
                found_via_synonym = False
                for term in synonyms:
                    escaped_term = re.escape(term.lower())
                    pattern = re.compile(rf'(?<![a-z0-9]){escaped_term}(?![a-z0-9])', re.IGNORECASE)
                    if pattern.search(cv_lower):
                        skill_dict["status"] = "FOUND"
                        skill_dict["source"] = "GRAPH_SYNONYM_SEARCH"
                        skill_dict["proof_excerpt"] = f"Synonyme détecté : '{term}'"
                        skill_dict["audit_status"] = "VALIDATED"
                        found_via_synonym = True
                        break
                
                if not found_via_synonym:
                    if len(skill.skill_name) > 2 and self.graph.check_skill_inference(skill.skill_name, cv_text):
                        skill_dict["status"] = "INFERRED"
                        skill_dict["source"] = "GRAPH_INFERENCE"
                        skill_dict["proof_excerpt"] = "Inférence logique déduite par l'Ontologie Neo4j."
                        skill_dict["audit_status"] = "VALIDATED"
                    else:
                        skill_dict["source"] = "UNKNOWN"
            else:
                if skill_dict["status"] != "MISSING":
                    skill_dict["source"] = "CV_TEXT"
                else:
                    skill_dict["source"] = "UNKNOWN"
            
            final_skills.append(skill_dict)

        return final_skills