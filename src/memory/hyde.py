import os  
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_groq import ChatGroq  # <--- AJOUTE CETTE LIGNE

load_dotenv()

class HydeGenerator:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0.7, # Un peu de créativité pour varier le vocabulaire
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY")
        )

    def generate_hypothetical_cvs(self, job_description: str) -> str:
        """
        Génère deux CVs fictifs (FR et EN) basés sur l'offre.
        Retourne une chaîne concaténée optimisée pour le vector search.
        """
        print("🔮 Génération des CVs fictifs via HyDE...")
        
        prompt = ChatPromptTemplate.from_template("""
        Tu es un expert en recrutement international.
        Ton objectif est d'aider un moteur de recherche vectoriel à trouver le candidat idéal.
        
        OFFRE D'EMPLOI :
        {job_desc}
        
        TACHE :
        Rédige DEUX profils "résumés" idéaux pour ce poste.
        1. Le premier profil doit être rédigé en FRANÇAIS professionnel.
        2. Le second profil doit être rédigé en ANGLAIS professionnel.
        
        Utilise le jargon technique précis, les soft skills attendus et les mots-clés de l'industrie.
        N'invente pas de nom, juste le contenu : "Expérience en...", "Expertise in...".
        
        FORMAT DE SORTIE :
        [PROFIL FR]
        ... contenu ...
        [PROFIL EN]
        ... content ...
        """)

        chain = prompt | self.llm
        result = chain.invoke({"job_desc": job_description})
        return result.content