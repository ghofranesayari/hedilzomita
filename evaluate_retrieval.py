import os
import json
import math
import pandas as pd
from pathlib import Path
from src.memory.vector_db import VectorDBManager
from src.memory.hyde import HydeGenerator
from src.ingestion.parser import ContentParser

# --- FONCTIONS MATHÉMATIQUES (MÉTRIQUES IR) ---

def calculate_mrr(retrieved_ids, qrels):
    for rank, cid in enumerate(retrieved_ids, 1):
        if qrels.get(cid, 0) > 0:
            return 1.0 / rank
    return 0.0

def calculate_precision_at_k(retrieved_ids, qrels, k):
    top_k = retrieved_ids[:k]
    relevant_count = sum(1 for cid in top_k if qrels.get(cid, 0) > 0)
    return relevant_count / k if k > 0 else 0.0

def calculate_recall_at_k(retrieved_ids, qrels, k):
    top_k = retrieved_ids[:k]
    total_relevant_in_db = sum(1 for v in qrels.values() if v > 0)
    if total_relevant_in_db == 0: return 1.0 
    
    relevant_found = sum(1 for cid in top_k if qrels.get(cid, 0) > 0)
    return relevant_found / total_relevant_in_db

def calculate_ndcg_at_k(retrieved_ids, qrels, k):
    dcg = 0.0
    for i, cid in enumerate(retrieved_ids[:k]):
        rel = qrels.get(cid, 0)
        dcg += ( (2**rel - 1) / math.log2(i + 2) ) 
        
    ideal_rels = sorted(list(qrels.values()), reverse=True)[:k]
    idcg = sum( ( (2**rel - 1) / math.log2(i + 2) ) for i, rel in enumerate(ideal_rels) )
    
    return dcg / idcg if idcg > 0 else 0.0


# --- PIPELINE DE VALIDATION ---

def run_benchmark(ground_truth_path="data/evaluation/ground_truth.json", top_k=3):
    print("="*80)
    print(" DÉMARRAGE DU BENCHMARK V6 (FAISS vs BM25 vs HYBRID vs HyDE)")
    print("="*80)
    
    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
        
    vdb = VectorDBManager("data/vector_store")
    hyde = HydeGenerator()
    parser = ContentParser()
    
    results_list = []

    for job in ground_truth:
        job_id = job["job_id"]
        qrels = job["qrels"]
        print(f"\n Analyse de la requête : {job_id}")
        
        try:
            job_text = parser.parse_pdf(Path(job["job_filepath"]))
        except Exception as e:
            print(f" Erreur lecture PDF {job['job_filepath']} : {e}")
            continue

        # 1. RUN FAISS PUR (Ancienne méthode)
        print("   -> Run 1 : FAISS Pur (100% Sémantique)...")
        res_faiss = vdb.search(job_text, k=top_k, weight_faiss=1.0, weight_bm25=0.0)
        ids_faiss = [r["candidate_id"] for r in res_faiss]
        
        # 2. RUN BM25 PUR
        print("   -> Run 2 : BM25 Pur (100% Mots-clés)...")
        res_bm25 = vdb.search(job_text, k=top_k, weight_faiss=0.0, weight_bm25=1.0)
        ids_bm25 = [r["candidate_id"] for r in res_bm25]
        
        # 3. RUN HYBRIDE (Texte Brut de l'offre)
        print("   -> Run 3 : Hybride (70% FAISS + 30% BM25)...")
        res_hybrid = vdb.search(job_text, k=top_k, weight_faiss=0.7, weight_bm25=0.3)
        ids_hybrid = [r["candidate_id"] for r in res_hybrid]

        # 4. RUN HYBRIDE + HyDE (La V6 ultime)
        print("   -> Run 4 : Hybride + HyDE (Génération CV fictif)...")
        hyde_text = hyde.generate_hypothetical_cvs(job_text)
        res_hyde = vdb.search(hyde_text, k=top_k, weight_faiss=0.7, weight_bm25=0.3)
        ids_hyde = [r["candidate_id"] for r in res_hyde]
        
        # CALCUL DES MÉTRIQUES POUR LES 4 MÉTHODES
        methods = [
            ("1_FAISS_Pur", ids_faiss),
            ("2_BM25_Pur", ids_bm25),
            ("3_Hybride", ids_hybrid),
            ("4_Hybride_HyDE", ids_hyde)
        ]
        
        for method_name, retrieved_ids in methods:
            mrr = calculate_mrr(retrieved_ids, qrels)
            ndcg = calculate_ndcg_at_k(retrieved_ids, qrels, top_k)
            prec = calculate_precision_at_k(retrieved_ids, qrels, top_k)
            rec = calculate_recall_at_k(retrieved_ids, qrels, top_k)
            
            results_list.append({
                "Job_ID": job_id,
                "Method": method_name,
                f"MRR@{top_k}": round(mrr, 3),
                f"NDCG@{top_k}": round(ndcg, 3),
                f"Precision@{top_k}": round(prec, 3),
                f"Recall@{top_k}": round(rec, 3)
            })

    # --- AFFICHAGE DU RAPPORT FINAL ---
    df = pd.DataFrame(results_list)
    
    print("\n" + "="*80)
    print(" RÉSULTATS DE L'ÉTUDE D'ABLATION (Comparaison des 4 Moteurs)")
    print("="*80)
    print(df.to_string(index=False))
    
    print("\n MOYENNES GLOBALES (Sur l'ensemble des offres)")
    summary = df.groupby("Method").mean(numeric_only=True).round(3)
    print(summary)
    
    os.makedirs("outputs/benchmark", exist_ok=True)
    df.to_csv("outputs/benchmark/faiss_bm25_hyde_evaluation.csv", index=False)
    print("\n Résultats sauvegardés dans outputs/benchmark/faiss_bm25_hyde_evaluation.csv")

if __name__ == "__main__":
    run_benchmark("data/evaluation/ground_truth.json", top_k=3)