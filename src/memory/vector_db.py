import hashlib
import json
import os
from typing import Dict, List

import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

from src.schemas.candidate import CandidateDigitalTwin


class VectorDBManager:
    INDEX_FILE = "index.faiss"
    DOCSTORE_FILE = "docstore.json"
    IDMAP_FILE = "index_to_docstore_id.json"
    BM25_FILE = "bm25_data.json"
    MANIFEST_FILE = "integrity_manifest.json"

    def __init__(self, index_path: str = "data/vector_store"):
        self.index_path = index_path
        print(" Chargement du modele d'embedding (paraphrase-multilingual-mpnet-base-v2)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        self.db = None
        self.bm25 = None
        self.corpus_metadata = []
        self.tokenized_corpus = []

    def index_candidates(self, candidates: List[CandidateDigitalTwin]):
        docs = []
        corpus_texts = []
        self.corpus_metadata = []

        for c in candidates:
            content = c.cv_text.strip()
            if not content or len(content) < 50:
                print(f" Candidat {c.candidate_id} ignore: CV vide ou trop court.")
                continue

            meta = {
                "candidate_id": c.candidate_id,
                "language": c.language,
                "filename": c.original_filename_id,
            }

            docs.append(Document(page_content=content, metadata=meta))
            corpus_texts.append(content.lower().split())
            self.corpus_metadata.append(meta)

        if not docs:
            print(" Aucun document valide a indexer.")
            return

        print(f" Indexation HYBRIDE de {len(docs)} CVs en cours...")

        self.db = FAISS.from_documents(docs, self.embeddings)
        self.bm25 = BM25Okapi(corpus_texts)
        self.tokenized_corpus = corpus_texts

        self._save()
        print(f" Index Hybride (FAISS + BM25) sauvegarde dans {self.index_path}")

    def search(self, query_vector: str, k: int = 5, weight_faiss=0.7, weight_bm25=0.3) -> List[Dict]:
        """Recherche hybride: FAISS (70%) + BM25 (30%)."""
        if not self.db or not self.bm25:
            try:
                self._load()
            except Exception as e:
                print(f" Impossible de charger l'index : {e}")
                return []

        total_docs = len(self.corpus_metadata)
        if total_docs == 0:
            return []

        # 1) FAISS semantic score
        faiss_results = self.db.similarity_search_with_score(query_vector, k=total_docs)
        faiss_scores = {}
        for doc, dist in faiss_results:
            cid = doc.metadata.get("candidate_id")
            if cid:
                faiss_scores[cid] = dist

        # Normalize FAISS (distance -> similarity)
        if faiss_scores:
            max_dist = max(faiss_scores.values())
            min_dist = min(faiss_scores.values())
            for cid in faiss_scores:
                if max_dist == min_dist:
                    faiss_scores[cid] = 1.0
                else:
                    faiss_scores[cid] = 1.0 - ((faiss_scores[cid] - min_dist) / (max_dist - min_dist))

        # 2) BM25 keyword score
        tokenized_query = query_vector.lower().split()
        bm25_raw = self.bm25.get_scores(tokenized_query)

        bm25_scores = {}
        for i, score in enumerate(bm25_raw):
            if i < len(self.corpus_metadata):
                cid = self.corpus_metadata[i]["candidate_id"]
                bm25_scores[cid] = score

        # Normalize BM25
        if bm25_scores:
            max_bm25 = max(bm25_scores.values())
            min_bm25 = min(bm25_scores.values())
            for cid in bm25_scores:
                if max_bm25 == min_bm25 or max_bm25 == 0:
                    bm25_scores[cid] = 0.0
                else:
                    bm25_scores[cid] = (bm25_scores[cid] - min_bm25) / (max_bm25 - min_bm25)

        # 3) Weighted fusion
        hybrid_results = []
        for meta in self.corpus_metadata:
            cid = meta["candidate_id"]

            f_score = faiss_scores.get(cid, 0.0)
            b_score = bm25_scores.get(cid, 0.0)
            final_score = (f_score * weight_faiss) + (b_score * weight_bm25)

            doc_content = "Preview non disponible."
            for _doc_id, doc in self.db.docstore._dict.items():
                if doc.metadata.get("candidate_id") == cid:
                    doc_content = doc.page_content[:200].replace("\n", " ") + "..."
                    break

            hybrid_results.append(
                {
                    "candidate_id": cid,
                    "filename": meta.get("filename", "Unknown"),
                    "score": final_score,
                    "preview": doc_content,
                    "faiss_detail": f_score,
                    "bm25_detail": b_score,
                }
            )

        hybrid_results = sorted(hybrid_results, key=lambda x: x["score"], reverse=True)
        return hybrid_results[:k]

    def _save(self):
        """Secure persistent save: FAISS + BM25 + SHA256 manifest."""
        if not self.db:
            raise ValueError("Impossible de sauvegarder: index FAISS absent.")
        if not self.bm25:
            raise ValueError("Impossible de sauvegarder: index BM25 absent.")

        os.makedirs(self.index_path, exist_ok=True)

        index_file = os.path.join(self.index_path, self.INDEX_FILE)
        docstore_file = os.path.join(self.index_path, self.DOCSTORE_FILE)
        idmap_file = os.path.join(self.index_path, self.IDMAP_FILE)
        bm25_file = os.path.join(self.index_path, self.BM25_FILE)
        manifest_file = os.path.join(self.index_path, self.MANIFEST_FILE)

        # 1) Save binary FAISS index (no pickle)
        faiss.write_index(self.db.index, index_file)

        # 2) Save docstore JSON
        serialized_docs = {}
        for doc_id, doc in self.db.docstore._dict.items():
            serialized_docs[str(doc_id)] = {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
        with open(docstore_file, "w", encoding="utf-8") as f:
            json.dump(serialized_docs, f, ensure_ascii=False, indent=2)

        # 3) Save index->doc mapping JSON
        with open(idmap_file, "w", encoding="utf-8") as f:
            json.dump(self.db.index_to_docstore_id, f, ensure_ascii=False, indent=2)

        # 4) Save BM25 data JSON (tokenized corpus + metadata)
        bm25_payload = {
            "tokenized_corpus": self.tokenized_corpus,
            "corpus_metadata": self.corpus_metadata,
        }
        with open(bm25_file, "w", encoding="utf-8") as f:
            json.dump(bm25_payload, f, ensure_ascii=False, indent=2)

        # 5) Save integrity manifest
        manifest = self._build_integrity_manifest([index_file, docstore_file, idmap_file, bm25_file])
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _load(self):
        """Secure load with strict integrity checks."""
        if not os.path.exists(self.index_path):
            raise ValueError("L'index vectoriel n'existe pas.")

        index_file = os.path.join(self.index_path, self.INDEX_FILE)
        docstore_file = os.path.join(self.index_path, self.DOCSTORE_FILE)
        idmap_file = os.path.join(self.index_path, self.IDMAP_FILE)
        bm25_file = os.path.join(self.index_path, self.BM25_FILE)
        manifest_file = os.path.join(self.index_path, self.MANIFEST_FILE)

        missing = [
            p
            for p in [index_file, docstore_file, idmap_file, bm25_file, manifest_file]
            if not os.path.exists(p)
        ]
        if missing:
            raise ValueError(
                "Index securise incomplet. Lancez reindex.py pour regenerer les artefacts: "
                + ", ".join(missing)
            )

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self._verify_integrity_manifest(manifest, [index_file, docstore_file, idmap_file, bm25_file])

        # 1) Load FAISS index directly
        index = faiss.read_index(index_file)

        # 2) Rebuild docstore and map
        with open(docstore_file, "r", encoding="utf-8") as f:
            raw_docs = json.load(f)
        with open(idmap_file, "r", encoding="utf-8") as f:
            raw_map = json.load(f)

        docs = {
            str(doc_id): Document(
                page_content=payload.get("page_content", ""),
                metadata=payload.get("metadata", {}),
            )
            for doc_id, payload in raw_docs.items()
        }
        docstore = InMemoryDocstore(docs)
        index_to_docstore_id = {int(k): str(v) for k, v in raw_map.items()}

        self.db = FAISS(self.embeddings, index, docstore, index_to_docstore_id)

        # 3) Rebuild BM25
        with open(bm25_file, "r", encoding="utf-8") as f:
            bm25_payload = json.load(f)

        self.tokenized_corpus = bm25_payload.get("tokenized_corpus", [])
        self.corpus_metadata = bm25_payload.get("corpus_metadata", [])
        if not self.tokenized_corpus:
            raise ValueError("BM25 corpus vide dans l'index securise.")
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    @staticmethod
    def _sha256_file(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _build_integrity_manifest(self, file_paths: List[str]) -> Dict:
        files = {}
        for p in file_paths:
            files[os.path.basename(p)] = {
                "sha256": self._sha256_file(p),
                "size_bytes": os.path.getsize(p),
            }
        return {
            "version": "vector_store_secure_v1",
            "files": files,
        }

    def _verify_integrity_manifest(self, manifest: Dict, file_paths: List[str]) -> None:
        files_info = manifest.get("files", {})
        if not files_info:
            raise ValueError("Manifest d'integrite invalide: section files absente.")

        for p in file_paths:
            fname = os.path.basename(p)
            expected = files_info.get(fname, {})
            expected_hash = expected.get("sha256", "")
            if not expected_hash:
                raise ValueError(f"Manifest incomplet: hash manquant pour {fname}.")

            current_hash = self._sha256_file(p)
            if current_hash != expected_hash:
                raise ValueError(
                    f"Integrite echouee pour {fname}. Reindex requis avant chargement."
                )
