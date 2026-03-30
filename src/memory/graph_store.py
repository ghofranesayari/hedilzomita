import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Force .env values to avoid hidden/stale OS env vars overriding credentials.
load_dotenv(override=True)

class GraphStore:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def setup_database(self):
        """
        Initialise les contraintes de schéma (Index).
        """
        print(" Initialisation du Schéma Neo4j (Index & Contraintes)...")
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Degree) REQUIRE d.name IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (s:Skill) ON (s.category)"
        ]
        
        with self.driver.session() as session:
            for q in queries:
                session.run(q)
        print(" Schéma Base de Données : PROPRE et OPTIMISÉ.")

    def initialize_ontology(self):
        """
        Charge l'Ontologie Métier (Règles d'équivalence et d'implication).
        Correction syntaxe Cypher : Utilisation de // pour les commentaires.
        """
        print(" Initialisation de l'Ontologie Expert (Bio-Pharma)...")
        queries = [
            # 1. Règles Académiques (Diplômes & Soft Skills)
            """
            MERGE (d1:Degree {name: 'PhD'})
            MERGE (d2:Degree {name: 'Pharmaceutical Sciences'})
            MERGE (d3:Degree {name: 'Biochemistry'})
            
            // PhD implique des soft skills de haut niveau
            MERGE (s1:Skill {name: 'Gestion de Projet Complexe'})
            MERGE (s2:Skill {name: 'Communication Scientifique'})
            MERGE (s3:Skill {name: 'Résilience'})
            
            MERGE (d1)-[:IMPLIES {confidence: 0.9, type: 'soft'}]->(s1)
            MERGE (d1)-[:IMPLIES {confidence: 0.8, type: 'soft'}]->(s2)
            MERGE (d1)-[:IMPLIES {confidence: 0.9, type: 'soft'}]->(s3)
            
            // Variations de PhD
            MERGE (d_pharma:Degree {name: 'PhD Pharmaceutical Sciences'})
            MERGE (d_bio:Degree {name: 'PhD Biochemistry'})
            MERGE (d1)-[:IS_EQUIVALENT_TO]-(d_pharma)
            MERGE (d1)-[:IS_EQUIVALENT_TO]-(d_bio)
            
            // Équivalences Domaines
            MERGE (d2)-[:IS_EQUIVALENT_TO {confidence: 1.0}]->(d3)
            """,
            
            # 2. Règles Métiers (Hard Skills Implicites)
            """
            MERGE (sk1:Skill {name: 'GMP'})
            MERGE (sk2:Skill {name: 'SOP'})
            MERGE (sk3:Skill {name: 'GLP'})
            
            // Si on connait GMP ou GLP, on connait forcément SOP
            MERGE (sk1)-[:IMPLIES {confidence: 1.0}]->(sk2)
            MERGE (sk3)-[:IMPLIES {confidence: 1.0}]->(sk2)
            """
        ]

        with self.driver.session() as session:
            for q in queries:
                session.run(q)
        print(" Ontologie Expert chargée.")

    def check_skill_inference(self, skill_name: str, cv_text: str) -> bool:
        cv_text = cv_text.lower()
        
        # 1. Détection Diplôme
        target_degree = None
        if "pharmaceutical sciences" in cv_text:
            target_degree = "Pharmaceutical Sciences"
        elif "phd" in cv_text:
            target_degree = "PhD"
            
        if not target_degree:
            return False

        # Requête Cypher
        query = """
        MATCH (d:Degree {name: $degree})
        OPTIONAL MATCH (d)-[:IS_EQUIVALENT_TO]-(d_eq:Degree)
        WITH d, d_eq
        MATCH (source)-[:IMPLIES]->(s:Skill)
        WHERE (source = d OR source = d_eq) AND toLower(s.name) CONTAINS toLower($skill)
        RETURN count(s) > 0 as is_inferred
        """
        with self.driver.session() as session:
            result = session.run(query, degree=target_degree, skill=skill_name)
            record = result.single()
            return record["is_inferred"] if record else False
        
    def infer_skills_from_education(self, education_text: str) -> list:
        inferred_skills = []
        education_text = education_text.lower()
        
        target_degree = None
        if "phd" in education_text or "doctorat" in education_text:
            target_degree = "PhD"
        elif "master" in education_text:
            target_degree = "Master"
            
        if target_degree:
            query = """
            MATCH (d:Degree {name: $degree})-[:IMPLIES]->(s:Skill)
            RETURN s.name as skill
            """
            with self.driver.session() as session:
                result = session.run(query, degree=target_degree)
                inferred_skills = [record["skill"] for record in result]
                
        return inferred_skills

    def node_exists(self, skill_name: str) -> bool:
        query = "MATCH (s:Skill) WHERE toLower(s.name) = toLower($name) RETURN count(s) > 0 as exists"
        with self.driver.session() as session:
            result = session.run(query, name=skill_name)
            return result.single()["exists"]

    def get_synonyms_and_related(self, skill_name: str) -> list:
        query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) CONTAINS toLower($name)
        OPTIONAL MATCH (s)-[:IS_EQUIVALENT_TO]-(syn:Skill)
        OPTIONAL MATCH (s)-[:RELATED_TO]-(rel:Skill)
        RETURN collect(DISTINCT syn.name) + collect(DISTINCT rel.name) as terms
        """
        with self.driver.session() as session:
            result = session.run(query, name=skill_name)
            record = result.single()
            terms = [t for t in record["terms"] if t] if record else []
            return list(set(terms))

    def get_definitions_context(self, skill_names: list) -> str:
        if not skill_names:
            return ""

        query = """
        MATCH (s:Skill)
        WHERE s.name IN $names
        OPTIONAL MATCH (s)-[:IS_EQUIVALENT_TO]-(syn:Skill)
        RETURN s.name as skill, s.category as cat, collect(syn.name) as synonyms
        """
        
        context_lines = []
        with self.driver.session() as session:
            result = session.run(query, names=skill_names)
            for record in result:
                syns = ", ".join([x for x in record["synonyms"] if x])
                line = f"- **{record['skill']}**: Category='{record['cat'] or 'Unknown'}'. Synonyms=[{syns}]."
                context_lines.append(line)
        
        return "\n".join(context_lines)
