
import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

class VectorEngine:
    # --- CHANGEMENT V2 : Modèle optimisé pour la mémoire ---
    # Ancien : "BAAI/bge-base-en-v1.5" (Trop lourd)
    # Nouveau : "all-MiniLM-L6-v2" (Léger et rapide)
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        # Initialize the embedding model (local execution)
        print(f"📉 Chargement du modèle vectoriel léger : {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.candidate_ids = []
        
        # Professional Path Resolution
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(os.path.dirname(script_dir))
        self.index_path = os.path.join(self.project_root, "data", "vault", "faiss_index.bin")
        self.map_path = os.path.join(self.project_root, "data", "vault", "index_map.json")

    def _extract_cv_only(self, full_text):
        """
        Expert Logic: Isolates CV content from the combined document.
        Assumes your ingestion marked sections or uses the first 60% of text as CV.
        """
        # For this implementation, we target the text before the 'Pitch' markers
        parts = full_text.split("Document 2:") # Standard marker from our TwinBuilder
        return parts[0] if len(parts) > 0 else full_text

    def create_index(self, work_copy_dir):
        """Iterates through work_copy, embeds CVs, and builds FAISS index."""
        embeddings = []
        self.candidate_ids = []

        print("🚀 Starting Vector Indexing (CV-Only Mode)...")

        for filename in os.listdir(work_copy_dir):
            if filename.endswith("_full_text.txt"):
                cid = filename.replace("_full_text.txt", "")
                file_path = os.path.join(work_copy_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # FOCUS: Only embed the CV portion
                cv_text = self._extract_cv_only(content)
                
                # Normalisation pour la similarité cosinus
                vector = self.model.encode(cv_text, normalize_embeddings=True)
                
                embeddings.append(vector)
                self.candidate_ids.append(cid)

        if not embeddings:
            print("⚠️ Aucun fichier trouvé pour l'indexation.")
            return

        # Build the FAISS Index (Inner Product for cosine similarity)
        dim = len(embeddings[0])
        self.index = faiss.IndexFlatIP(dim) 
        self.index.add(np.array(embeddings).astype('float32'))

        # Save for persistence
        faiss.write_index(self.index, self.index_path)
        with open(self.map_path, 'w') as f:
            json.dump(self.candidate_ids, f)

        print(f"✅ Indexed {len(self.candidate_ids)} candidates into FAISS.")

    def search(self, query_text, top_k=5):
        """Searches the index for the most similar CVs."""
        if not self.index:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.map_path, 'r') as f:
                    self.candidate_ids = json.load(f)
            else:
                print("⚠️ Index non trouvé. Veuillez lancer l'indexation d'abord.")
                return []

        # Encodage de la requête avec le même modèle
        query_vector = self.model.encode(query_text, normalize_embeddings=True)
        
        # Recherche FAISS
        distances, indices = self.index.search(np.array([query_vector]).astype('float32'), top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            # Protection contre les index hors limites
            if idx < len(self.candidate_ids) and idx != -1:
                results.append({
                    "candidate_id": self.candidate_ids[idx],
                    "score": float(distances[0][i])
                })
        return results

if __name__ == "__main__":
    # Internal Test : Re-création de l'index avec le nouveau modèle
    engine = VectorEngine()
    work_dir = os.path.join(engine.project_root, "data", "work_copy")
    engine.create_index(work_dir)


# import os
# import json
# import faiss
# import numpy as np
# from sentence_transformers import SentenceTransformer
# from dotenv import load_dotenv, find_dotenv

# load_dotenv(find_dotenv())

# class VectorEngine:
#     def __init__(self, model_name="BAAI/bge-base-en-v1.5"):
#         # Initialize the embedding model (local execution)
#         self.model = SentenceTransformer(model_name)
#         self.index = None
#         self.candidate_ids = []
        
#         # Professional Path Resolution
#         script_dir = os.path.dirname(os.path.abspath(__file__))
#         self.project_root = os.path.dirname(os.path.dirname(script_dir))
#         self.index_path = os.path.join(self.project_root, "data", "vault", "faiss_index.bin")
#         self.map_path = os.path.join(self.project_root, "data", "vault", "index_map.json")

#     def _extract_cv_only(self, full_text):
#         """
#         Expert Logic: Isolates CV content from the combined document.
#         Assumes your ingestion marked sections or uses the first 60% of text as CV.
#         """
#         # For this implementation, we target the text before the 'Pitch' markers
#         parts = full_text.split("Document 2:") # Standard marker from our TwinBuilder
#         return parts[0] if len(parts) > 0 else full_text

#     def create_index(self, work_copy_dir):
#         """Iterates through work_copy, embeds CVs, and builds FAISS index."""
#         embeddings = []
#         self.candidate_ids = []

#         print(" Starting Vector Indexing (CV-Only Mode)...")

#         for filename in os.listdir(work_copy_dir):
#             if filename.endswith("_full_text.txt"):
#                 cid = filename.replace("_full_text.txt", "")
#                 with open(os.path.join(work_copy_dir, filename), 'r', encoding='utf-8') as f:
#                     content = f.read()
                    
#                 # FOCUS: Only embed the CV portion
#                 cv_text = self._extract_cv_only(content)
#                 vector = self.model.encode(cv_text, normalize_embeddings=True)
                
#                 embeddings.append(vector)
#                 self.candidate_ids.append(cid)

#         # Build the FAISS Index (L2 Distance or Inner Product)
#         dim = len(embeddings[0])
#         self.index = faiss.IndexFlatIP(dim) # Inner Product for cosine similarity
#         self.index.add(np.array(embeddings).astype('float32'))

#         # Save for persistence
#         faiss.write_index(self.index, self.index_path)
#         with open(self.map_path, 'w') as f:
#             json.dump(self.candidate_ids, f)

#         print(f"✅ Indexed {len(self.candidate_ids)} candidates into FAISS.")

#     def search(self, query_text, top_k=5):
#         """Searches the index for the most similar CVs."""
#         if not self.index:
#             self.index = faiss.read_index(self.index_path)
#             with open(self.map_path, 'r') as f:
#                 self.candidate_ids = json.load(f)

#         query_vector = self.model.encode(query_text, normalize_embeddings=True)
#         distances, indices = self.index.search(np.array([query_vector]).astype('float32'), top_k)

#         results = []
#         for i, idx in enumerate(indices[0]):
#             results.append({
#                 "candidate_id": self.candidate_ids[idx],
#                 "score": float(distances[0][i])
#             })
#         return results

# if __name__ == "__main__":
#     # Internal Test
#     engine = VectorEngine()
#     work_dir = os.path.join(engine.project_root, "data", "work_copy")
#     engine.create_index(work_dir)





# import os
# import json
# import faiss
# import numpy as np
# from sentence_transformers import SentenceTransformer
# from dotenv import load_dotenv, find_dotenv

# load_dotenv(find_dotenv())

# class VectorEngine:
#     # --- CHANGEMENT V2 : Modèle optimisé pour la mémoire ---
#     # Ancien : "BAAI/bge-base-en-v1.5" (Trop lourd)
#     # Nouveau : "all-MiniLM-L6-v2" (Léger et rapide)
#     def __init__(self, model_name="all-MiniLM-L6-v2"):
#         # Initialize the embedding model (local execution)
#         print(f"📉 Chargement du modèle vectoriel léger : {model_name}...")
#         self.model = SentenceTransformer(model_name)
#         self.index = None
#         self.candidate_ids = []
        
#         # Professional Path Resolution
#         script_dir = os.path.dirname(os.path.abspath(__file__))
#         self.project_root = os.path.dirname(os.path.dirname(script_dir))
#         self.index_path = os.path.join(self.project_root, "data", "vault", "faiss_index.bin")
#         self.map_path = os.path.join(self.project_root, "data", "vault", "index_map.json")

#     def _extract_cv_only(self, full_text):
#         """
#         Expert Logic: Isolates CV content from the combined document.
#         Assumes your ingestion marked sections or uses the first 60% of text as CV.
#         """
#         # For this implementation, we target the text before the 'Pitch' markers
#         parts = full_text.split("Document 2:") # Standard marker from our TwinBuilder
#         return parts[0] if len(parts) > 0 else full_text

#     def create_index(self, work_copy_dir):
#         """Iterates through work_copy, embeds CVs, and builds FAISS index."""
#         embeddings = []
#         self.candidate_ids = []

#         print("🚀 Starting Vector Indexing (CV-Only Mode)...")

#         for filename in os.listdir(work_copy_dir):
#             if filename.endswith("_full_text.txt"):
#                 cid = filename.replace("_full_text.txt", "")
#                 file_path = os.path.join(work_copy_dir, filename)
                
#                 with open(file_path, 'r', encoding='utf-8') as f:
#                     content = f.read()
                    
#                 # FOCUS: Only embed the CV portion
#                 cv_text = self._extract_cv_only(content)
                
#                 # Normalisation pour la similarité cosinus
#                 vector = self.model.encode(cv_text, normalize_embeddings=True)
                
#                 embeddings.append(vector)
#                 self.candidate_ids.append(cid)

#         if not embeddings:
#             print("⚠️ Aucun fichier trouvé pour l'indexation.")
#             return

#         # Build the FAISS Index (Inner Product for cosine similarity)
#         dim = len(embeddings[0])
#         self.index = faiss.IndexFlatIP(dim) 
#         self.index.add(np.array(embeddings).astype('float32'))

#         # Save for persistence
#         faiss.write_index(self.index, self.index_path)
#         with open(self.map_path, 'w') as f:
#             json.dump(self.candidate_ids, f)

#         print(f"✅ Indexed {len(self.candidate_ids)} candidates into FAISS.")

#     def search(self, query_text, top_k=5):
#         """Searches the index for the most similar CVs."""
#         if not self.index:
#             if os.path.exists(self.index_path):
#                 self.index = faiss.read_index(self.index_path)
#                 with open(self.map_path, 'r') as f:
#                     self.candidate_ids = json.load(f)
#             else:
#                 print("⚠️ Index non trouvé. Veuillez lancer l'indexation d'abord.")
#                 return []

#         # Encodage de la requête avec le même modèle
#         query_vector = self.model.encode(query_text, normalize_embeddings=True)
        
#         # Recherche FAISS
#         distances, indices = self.index.search(np.array([query_vector]).astype('float32'), top_k)

#         results = []
#         for i, idx in enumerate(indices[0]):
#             # Protection contre les index hors limites
#             if idx < len(self.candidate_ids) and idx != -1:
#                 results.append({
#                     "candidate_id": self.candidate_ids[idx],
#                     "score": float(distances[0][i])
#                 })
#         return results

# if __name__ == "__main__":
#     # Internal Test : Re-création de l'index avec le nouveau modèle
#     engine = VectorEngine()
#     work_dir = os.path.join(engine.project_root, "data", "work_copy")
#     engine.create_index(work_dir)


# # import os
# # import json
# # import faiss
# # import numpy as np
# # from sentence_transformers import SentenceTransformer
# # from dotenv import load_dotenv, find_dotenv

# # load_dotenv(find_dotenv())

# # class VectorEngine:
# #     def __init__(self, model_name="BAAI/bge-base-en-v1.5"):
# #         # Initialize the embedding model (local execution)
# #         self.model = SentenceTransformer(model_name)
# #         self.index = None
# #         self.candidate_ids = []
        
# #         # Professional Path Resolution
# #         script_dir = os.path.dirname(os.path.abspath(__file__))
# #         self.project_root = os.path.dirname(os.path.dirname(script_dir))
# #         self.index_path = os.path.join(self.project_root, "data", "vault", "faiss_index.bin")
# #         self.map_path = os.path.join(self.project_root, "data", "vault", "index_map.json")

# #     def _extract_cv_only(self, full_text):
# #         """
# #         Expert Logic: Isolates CV content from the combined document.
# #         Assumes your ingestion marked sections or uses the first 60% of text as CV.
# #         """
# #         # For this implementation, we target the text before the 'Pitch' markers
# #         parts = full_text.split("Document 2:") # Standard marker from our TwinBuilder
# #         return parts[0] if len(parts) > 0 else full_text

# #     def create_index(self, work_copy_dir):
# #         """Iterates through work_copy, embeds CVs, and builds FAISS index."""
# #         embeddings = []
# #         self.candidate_ids = []

# #         print(" Starting Vector Indexing (CV-Only Mode)...")

# #         for filename in os.listdir(work_copy_dir):
# #             if filename.endswith("_full_text.txt"):
# #                 cid = filename.replace("_full_text.txt", "")
# #                 with open(os.path.join(work_copy_dir, filename), 'r', encoding='utf-8') as f:
# #                     content = f.read()
                    
# #                 # FOCUS: Only embed the CV portion
# #                 cv_text = self._extract_cv_only(content)
# #                 vector = self.model.encode(cv_text, normalize_embeddings=True)
                
# #                 embeddings.append(vector)
# #                 self.candidate_ids.append(cid)

# #         # Build the FAISS Index (L2 Distance or Inner Product)
# #         dim = len(embeddings[0])
# #         self.index = faiss.IndexFlatIP(dim) # Inner Product for cosine similarity
# #         self.index.add(np.array(embeddings).astype('float32'))

# #         # Save for persistence
# #         faiss.write_index(self.index, self.index_path)
# #         with open(self.map_path, 'w') as f:
# #             json.dump(self.candidate_ids, f)

# #         print(f"✅ Indexed {len(self.candidate_ids)} candidates into FAISS.")

# #     def search(self, query_text, top_k=5):
# #         """Searches the index for the most similar CVs."""
# #         if not self.index:
# #             self.index = faiss.read_index(self.index_path)
# #             with open(self.map_path, 'r') as f:
# #                 self.candidate_ids = json.load(f)

# #         query_vector = self.model.encode(query_text, normalize_embeddings=True)
# #         distances, indices = self.index.search(np.array([query_vector]).astype('float32'), top_k)

# #         results = []
# #         for i, idx in enumerate(indices[0]):
# #             results.append({
# #                 "candidate_id": self.candidate_ids[idx],
# #                 "score": float(distances[0][i])
# #             })
# #         return results

# # if __name__ == "__main__":
# #     # Internal Test
# #     engine = VectorEngine()
# #     work_dir = os.path.join(engine.project_root, "data", "work_copy")
# #     engine.create_index(work_dir)