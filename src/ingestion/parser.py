import pandas as pd
from docling.document_converter import DocumentConverter
from pathlib import Path
from src.schemas.candidate import PreferenceData

class ContentParser:
    def __init__(self):
        self.converter = DocumentConverter() # Docling Initialization

    def parse_pdf(self, file_path: Path) -> str:
        """Utilise Docling pour extraire le texte structuré (Markdown)."""
        try:
            result = self.converter.convert(file_path)
            # Export en Markdown pour garder la structure (Titres, Listes) pour le LLM
            return result.document.export_to_markdown()
        except Exception as e:
            print(f"⚠️ Erreur parsing PDF {file_path.name}: {e}")
            return ""

    def parse_excel_row(self, row: pd.Series) -> PreferenceData:
        """Version optimisée pour les en-têtes complexes de l'enquête."""
        
        def safe_get(key_part):
            for col in row.index:
                if key_part.lower() in str(col).lower():
                    return row[col]
            return None

        # 1. Extraction et nettoyage des listes (gestion des virgules ET retours à la ligne)
        def clean_list(value):
            if not value or pd.isna(value) or str(value).lower() == 'n/a':
                return []
            # On sépare par virgule OU par retour à la ligne
            import re
            items = re.split(r'[,\n]', str(value))
            return [i.strip() for i in items if i.strip()]

        # 2. Mapping basé sur les colonnes réelles de tes captures
        # "Indicate your jobs..." est souvent la source des roles
        roles_raw = safe_get("Indicate your jobs") or safe_get("Preferred Roles")
        
        # "Which fields of activity..."
        fields_raw = safe_get("Which fields of activity")

        # "Top 5 Priorities" - Si c'est dans la même colonne que les jobs
        priorities = clean_list(roles_raw)

        return PreferenceData(
            preferred_roles=clean_list(roles_raw),
            top_priorities=priorities[:5], # On prend les 5 premiers
            salary_expectations=str(safe_get("What are your salary") or ""),
            fields_of_activity=clean_list(fields_raw),
            target_companies=str(safe_get("companies you’re particularly interested") or ""),
            application_history=str(safe_get("Where have you already applied") or ""),
            recent_interviews=str(safe_get("Have you had any interviews") or "")
        )

def load_excel_db(path: str) -> pd.DataFrame:
    return pd.read_excel(path)