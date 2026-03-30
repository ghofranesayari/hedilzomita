import os
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq

# 1. Le Schéma strict (Type Safety)
class JobMetadata(BaseModel):
    title: str = Field(description="Le titre exact du poste proposé")
    company_name: str = Field(description="Le nom de l'entreprise qui recrute")
    industry: str = Field(description="Le secteur d'activité principal (ex: Pharmaceutique, Informatique, Aéronautique)")
    salary_max: float = Field(description="Le salaire maximum mentionné. Mettre 0.0 si aucun salaire n'est indiqué.")

class JobParserAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key: 
            raise ValueError(" GROQ_API_KEY manquante.")
            
        # Initialisation directe de Groq (comme vos autres agents)
        self.llm = ChatGroq(
            temperature=0.0, 
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            api_key=api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=JobMetadata)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en Ressources Humaines.
            Lis l'offre d'emploi suivante et extrais les informations demandées.
            Si une information (comme le salaire) est manquante, respecte les instructions du format.
            
            Format attendu :
            {format_instructions}"""),
            ("human", "Offre d'emploi :\n{job_text}")
        ])
        
        self.chain = self.prompt | self.llm | self.parser

    def extract_metadata(self, job_text: str) -> dict:
        """Lit le texte brut du PDF et renvoie un dictionnaire propre."""
        print(" JobParser: Extraction automatique des métadonnées de l'offre...")
        try:
            # L'IA lit le texte et le transforme en objet structuré
            result = self.chain.invoke({
                "job_text": job_text,
                "format_instructions": self.parser.get_format_instructions()
            })
            # On le convertit en dictionnaire pour qu'il soit compatible avec l'Agent Logistique
            return result.model_dump()
        except Exception as e:
            print(f" Erreur d'extraction de l'offre : {e}")
            # Fallback de sécurité
            return {
                "title": "Inconnu", 
                "company_name": "Inconnu", 
                "industry": "Inconnu", 
                "salary_max": 0.0
            }