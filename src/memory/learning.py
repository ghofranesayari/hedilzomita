import os
from typing import Dict, List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from src.memory.graph_store import GraphStore


class ConceptDefinition(BaseModel):
    term: str = Field(..., description="Le terme cible (ex: Absorption Spectroscopy)")
    category: str = Field(..., description="La categorie (ex: Methodology, Software, Framework)")
    synonyms: List[str] = Field(..., description="Outils methodes acronymes lies. Vide pour C, R.")
    related_concepts: List[str] = Field(..., description="Concepts lies.")


class NewKnowledge(BaseModel):
    concepts: List[ConceptDefinition]


class KnowledgeExpander:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0.1,
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY"),
        )
        self.graph = GraphStore()
        self.parser = PydanticOutputParser(pydantic_object=NewKnowledge)

    def learn_and_expand(self, target_skills: List[str], job_description: str = "") -> None:
        """Apprentissage cible: on apprend uniquement les skills inconnus."""
        print("\n KNOWLEDGE EXPANDER: Construction de l'ontologie cible...")

        unknowns: List[str] = []
        for term in target_skills:
            if not self.graph.node_exists(term):
                unknowns.append(term)

        if not unknowns:
            print("   Tous les termes sont deja connus du graphe.")
            return

        print(f"   Nouveaux concepts a decomposer : {unknowns}")

        system_prompt = """
        You are an Expert Ontologist across technical domains.
        Map these target skills: {terms}.
        Use this job context if useful: {job_context}

        For EACH term, define:
        1) category
        2) synonyms (specific tools/acronyms proving the skill)
           - if term is one-letter language (C, R), synonyms MUST be []
        3) related concepts

        OUTPUT FORMAT (JSON):
        {format_instructions}
        """

        prompt = ChatPromptTemplate.from_template(system_prompt)
        chain = prompt | self.llm | self.parser

        try:
            context_snippet = job_description[:2000] if job_description else "No context."
            knowledge = chain.invoke(
                {
                    "terms": unknowns,
                    "job_context": context_snippet,
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )
            self._inject_into_graph(knowledge)
        except Exception as exc:
            print(f" Erreur durant l'apprentissage : {exc}")

    def _inject_into_graph(self, knowledge: NewKnowledge) -> None:
        print("    Injection des connaissances dans Neo4j...")

        query_main = """
        MERGE (s:Skill {name: $term})
        SET s.category = $category, s.learned_at = timestamp()
        """

        query_synonym = """
        MERGE (main:Skill {name: $term})
        MERGE (syn:Skill {name: $synonym})
        MERGE (main)-[:IS_EQUIVALENT_TO {confidence: 1.0, origin: 'auto-learning'}]->(syn)
        """

        query_related = """
        MERGE (main:Skill {name: $term})
        MERGE (rel:Skill {name: $related})
        MERGE (main)-[:RELATED_TO {confidence: 0.8, origin: 'auto-learning'}]->(rel)
        """

        with self.graph.driver.session() as session:
            for concept in knowledge.concepts:
                term = str(concept.term or "").strip()
                category = str(concept.category or "Unknown").strip() or "Unknown"
                if not term:
                    continue

                if len(term) <= 2:
                    print(f"    Rejet automatique des synonymes pour '{term}' (anti-pollution).")
                    concept.synonyms = []

                session.run(query_main, term=term, category=category)

                for syn in concept.synonyms:
                    synonym = str(syn or "").strip()
                    if not synonym:
                        continue
                    session.run(query_synonym, term=term, synonym=synonym)

                for rel in concept.related_concepts:
                    related = str(rel or "").strip()
                    if not related:
                        continue
                    session.run(query_related, term=term, related=related)

        print(f"    Ontologie enrichie pour {len(knowledge.concepts)} concepts.")
