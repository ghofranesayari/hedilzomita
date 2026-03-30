import json
import os

from src.memory.vector_db import VectorDBManager
from src.schemas.candidate import CandidateDigitalTwin


def force_reindex():
    print(" DEMARRAGE DE LA REINDEXATION HYBRIDE (V6)...")

    vdb = VectorDBManager("data/vector_store")
    candidates = []
    processed_dir = "data/processed"

    if not os.path.exists(processed_dir):
        print(f" Le dossier {processed_dir} n'existe pas.")
        return

    # 1. Charger tous les candidats
    for filename in os.listdir(processed_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(processed_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates.append(CandidateDigitalTwin(**data))

    if not candidates:
        print(" Aucun candidat trouve dans data/processed.")
        return

    print(f" {len(candidates)} candidats charges en memoire.")

    # 2. Reindexation
    vdb.index_candidates(candidates)

    print(" MIGRATION TERMINEE ! Index securise regenere (FAISS + BM25 JSON + manifest).")


if __name__ == "__main__":
    force_reindex()
