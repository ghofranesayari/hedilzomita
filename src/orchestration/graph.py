from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import du Schéma d'État
from src.schemas.state import MatchingState

# Import des Nœuds mis à jour
from src.orchestration.nodes import (
    node_initializer,
    node_bridge,
    node_auditor,
    node_psycho,
    node_rhetoric,
    node_logistics,
    node_cv_global,
    node_role_recommender,
    node_aggregator,
    node_final_scoring
)

class AEBMGraphOrchestrator:
    def __init__(self):
        print(" [SYSTEM] Initialisation du Graphe Neuro-Symbolique V5...")
        
        # 1. Initialisation du Graphe
        self.workflow = StateGraph(MatchingState)
        
        # 2. Enregistrement des Nœuds
        self.workflow.add_node("initializer", node_initializer)
        self.workflow.add_node("bridge", node_bridge)
        self.workflow.add_node("auditor", node_auditor)
        
        # Branches parallèles
        self.workflow.add_node("psycho", node_psycho)
        self.workflow.add_node("rhetoric", node_rhetoric)
        self.workflow.add_node("logistics", node_logistics)
        self.workflow.add_node("cv_global", node_cv_global)
        self.workflow.add_node("role_recommender", node_role_recommender)
        
        # Convergence et Scoring
        self.workflow.add_node("aggregator", node_aggregator)
        self.workflow.add_node("final_scoring", node_final_scoring)

        # 3. Définition du Séquençage Initial
        self.workflow.add_edge(START, "initializer")
        self.workflow.add_edge("initializer", "bridge")
        self.workflow.add_edge("bridge", "auditor")

        # 4. Logique du Routeur Conditionnel (Boucle d'Audit)
        def _route_after_audit(state: MatchingState) -> List[str]:
            """Détermine si on doit corriger les preuves ou passer à l'analyse multi-dimensionnelle."""
            verdict = state.get("last_verdict", "VALIDATED")
            retries = state.get("retry_count", 0)
            
            if verdict == "REJECTED" and retries < 3:
                print(f"    [ROUTER] Qualité insuffisante (Essai {retries}). Retour au Bridge.")
                return ["bridge"]
            
            cid = state.get("candidate_id", "")
            if cid == "SELF_AUDIT_USER":
                print("    [ROUTER] Audit validé. Mode candidat: fan-out limité (CV + recommandations).")
                return ["cv_global", "role_recommender"]
            else:
                print("    [ROUTER] Audit validé. Mode interne: fan-out complet (sans recommandations).")
                return ["psycho", "rhetoric", "logistics", "cv_global"]

        self.workflow.add_conditional_edges(
            "auditor",
            _route_after_audit,
            {
                "bridge": "bridge", 
                "psycho": "psycho", 
                "rhetoric": "rhetoric", 
                "logistics": "logistics",
                "cv_global": "cv_global",
                "role_recommender": "role_recommender"
            }
        )

        # 5. Convergence (Fan-In)
        # LangGraph attend la fin des 3 branches avant d'exécuter aggregator
        self.workflow.add_edge("psycho", "aggregator")
        self.workflow.add_edge("rhetoric", "aggregator")
        self.workflow.add_edge("logistics", "aggregator")
        self.workflow.add_edge("cv_global", "aggregator")
        self.workflow.add_edge("role_recommender", "aggregator")
        
        self.workflow.add_edge("aggregator", "final_scoring")
        self.workflow.add_edge("final_scoring", END)

        # 6. Compilation avec Persistance et Breakpoint
        self.memory = MemorySaver()
        self.app = self.workflow.compile(
            checkpointer=self.memory,
            interrupt_before=["final_scoring"]  # Arrêt de sécurité pour validation humaine
        )
        print("✅ [SYSTEM] Graphe compilé. Breakpoint actif avant 'final_scoring'.")

    def run_pipeline(self, initial_state: Optional[dict], thread_id: str):
        """
        Exécute le pipeline. 
        Si initial_state est fourni, démarre de zéro.
        Si initial_state est None, reprend depuis le dernier checkpoint.
        """
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 20 
        }
        
        if initial_state:
            print(f"\n [START] Lancement du diagnostic : {initial_state.get('candidate_id', 'Unknown')}")
        else:
            print(f"\n [RESUME] Reprise du diagnostic (Post-Checkpoint)...")

        # Streaming des événements pour monitoring terminal
        try:
            for event in self.app.stream(initial_state, config=config, stream_mode="values"):
                # On peut logger ici l'évolution de l'état si nécessaire
                pass
            
            # Vérification de l'état actuel (si interrompu ou fini)
            final_state = self.app.get_state(config)
            
            if final_state.next:
                print(f"    [INTERRUPT] Pipeline en pause devant : {final_state.next}")
                return final_state.values
            
            print("    [FINISH] Pipeline terminé avec succès.")
            return final_state.values

        except Exception as e:
            print(f"   [FATAL] Erreur lors de l'exécution du graphe : {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_architecture_diag(self, base_path: str = "outputs/architecture"):
        """Génère les schémas de l'architecture du graphe."""
        try:
            output_dir = Path(base_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarde Mermaid
            mermaid_path = output_dir / "workflow_v5.mmd"
            mermaid_path.write_text(self.app.get_graph().draw_mermaid())
            
            # Sauvegarde PNG
            png_path = output_dir / "workflow_v5.png"
            png_path.write_bytes(self.app.get_graph().draw_mermaid_png())
            
            print(f" [DIAGRAMS] Architecture sauvegardée dans {base_path}")
        except Exception as e:
            print(f" [DIAGRAMS] Impossible de générer les images (manque probablement pygraphviz) : {e}")
