import os
import json
import re
from typing import List, Literal
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from src.schemas.state import SkillProof

class AuditResultItem(BaseModel):
    skill_name: str = Field(description="Nom exact de la compétence auditée.")
    audit_status: Literal["VALIDATED", "REJECTED"] = Field(description="Le verdict implacable.")
    comment: str = Field(description="Justification de la décision.")

class AuditResponse(BaseModel):
    results: List[AuditResultItem]

class CynicalAuditor:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY")
        )
        # INITIALISATION DU PARSER
        self.parser = PydanticOutputParser(pydantic_object=AuditResponse)

    def _sanitize_json_output(self, text: str) -> str:
        text = text.strip()
        if "```" in text:
            pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
            match = re.search(pattern, text, re.DOTALL)
            text = match.group(1) if match else text.split("```")[1]
        
        start = text.find("{")
        end = text.rfind("}")
        return text[start : end + 1] if start != -1 else text


    def audit(self, skills_data: list, cv_text: str, domain_context: str = "") -> tuple[list, str, str]:
        print(f" Cynical Auditor: Vérification avec contexte métier ({len(domain_context)} chars)...")
        
        to_verify = [s for s in skills_data if s['status'] == 'FOUND' and s['source'] in ['CV_TEXT', 'GRAPH_SYNONYM_SEARCH']]
        if not to_verify:
            return skills_data, "VALIDATED", "Aucune preuve textuelle à vérifier."

        # --- PROMPT MIS À JOUR POUR UTILISER PYDANTIC ---
        prompt_txt = """
        You are a Cynical Auditor. Verify if the 'Proof Excerpts' from a CV support the 'Skill' claimed.

        ###  DOMAIN CONTEXT (ABSOLUTE TRUTH)
        {domain_context}

        ### INPUT DATA
        - CV TEXT: {cv_text}
        - CLAIMS: {claims}

        ### VERIFICATION RULES BY CATEGORY:
        1. **For 'TOOL' & 'STANDARD':** Be extremely strict. The specific tool/standard MUST be explicitly named or validated by an EXACT synonym from the Domain Context. 
        2. **For 'RESPONSIBILITY':** Be semantically flexible. If the CV describes an action that clearly matches the English responsibility, ACCEPT it.
        3. **For 'ACADEMIC':** Be pragmatic. A "Diplôme d'ingénieur" in France/Canada is equivalent to a Master's or B.S. Accept highly related fields.

        ### OUTPUT FORMAT (JSON ONLY)
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_txt)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "cv_text": cv_text[:25000], 
                "claims": json.dumps(to_verify),
                "domain_context": domain_context if domain_context else "No specific context provided.",
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # 1. Utilisation OBLIGATOIRE du nettoyeur
            json_str = self._sanitize_json_output(response.content)
            
            # 2. Parsing Pydantic sécurisé
            parsed_data = self.parser.parse(json_str)
            audit_results = [item.model_dump() for item in parsed_data.results]
            
        except Exception as e:
            print(f" Erreur LLM Auditor: {e}")
            # Fail-closed: on ne valide jamais automatiquement une compétence
            # quand l'audit LLM est indisponible.
            for s in skills_data:
                if s['status'] == 'FOUND':
                    s['audit_status'] = 'UNVERIFIED'
                    s['audit_comment'] = "Audit indisponible: competence non validee automatiquement."
            return skills_data, "REJECTED", "Erreur technique auditeur (Fail-closed)."
        
        # Mise à jour des statuts
        global_status = "VALIDATED"
        feedback_loop = []
        audit_map = {res['skill_name']: res for res in audit_results}

        for skill in skills_data:
            if skill['skill_name'] in audit_map:
                res = audit_map[skill['skill_name']]
                skill['audit_status'] = res['audit_status']
                skill['audit_comment'] = res.get('comment', '')
                
                if res['audit_status'] == 'REJECTED':
                    global_status = "REJECTED"
                    feedback_loop.append(f"Skill '{skill['skill_name']}' rejected: {res.get('comment')}")
            
            elif skill['status'] == 'INFERRED':
                skill['audit_status'] = 'VALIDATED' 
                skill['audit_comment'] = 'Validé par Inférence Académique (Neo4j)'

        return skills_data, global_status, " ".join(feedback_loop)
