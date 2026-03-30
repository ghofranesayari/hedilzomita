from pathlib import Path

import pandas as pd
from pdfminer.high_level import extract_text as pdfminer_extract_text

from src.schemas.candidate import PreferenceData

try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
except Exception:  # pragma: no cover - keep parser resilient across envs
    DocumentConverter = None  # type: ignore[assignment]
    InputFormat = None  # type: ignore[assignment]
    PdfPipelineOptions = None  # type: ignore[assignment]
    RapidOcrOptions = None  # type: ignore[assignment]
    PdfFormatOption = None  # type: ignore[assignment]


class ContentParser:
    def __init__(self):
        self.converter = self._build_converter()

    def _build_converter(self):
        if DocumentConverter is None:
            return None

        if all(
            dependency is not None
            for dependency in (InputFormat, PdfPipelineOptions, RapidOcrOptions, PdfFormatOption)
        ):
            try:
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = True
                pipeline_options.ocr_options = RapidOcrOptions()
                return DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
            except Exception as exc:
                print(f"[PARSER] OCR Docling setup unavailable, fallback to default converter: {exc}")

        try:
            return DocumentConverter()
        except Exception as exc:
            print(f"[PARSER] Docling converter unavailable: {exc}")
            return None

    @staticmethod
    def has_usable_text(text: str, min_words: int = 20) -> bool:
        return bool(text and len(text.split()) >= min_words)

    @staticmethod
    def _extract_with_pdfminer(file_path: Path) -> str:
        try:
            text = pdfminer_extract_text(str(file_path)) or ""
            return text.strip()
        except Exception as exc:
            print(f"[PARSER] pdfminer fallback failed for {file_path.name}: {exc}")
            return ""

    def parse_pdf(self, file_path: Path) -> str:
        """Use Docling OCR first, then pdfminer as a fallback for text PDFs."""
        docling_text = ""

        if self.converter is not None:
            try:
                result = self.converter.convert(file_path)
                docling_text = (result.document.export_to_markdown() or "").strip()
                if self.has_usable_text(docling_text):
                    return docling_text
                if docling_text:
                    print(
                        f"[PARSER] Docling extracted only {len(docling_text.split())} words from {file_path.name}; "
                        "trying pdfminer fallback."
                    )
                else:
                    print(f"[PARSER] Docling returned empty content for {file_path.name}; trying pdfminer fallback.")
            except Exception as exc:
                print(f"[PARSER] Docling parsing failed for {file_path.name}: {exc}")

        fallback_text = self._extract_with_pdfminer(file_path)
        if self.has_usable_text(fallback_text):
            return fallback_text

        return (docling_text or fallback_text).strip()

    def parse_excel_row(self, row: pd.Series) -> PreferenceData:
        """Version optimisee pour les en-tetes complexes de l'enquete."""
        
        def safe_get(key_part):
            for col in row.index:
                if key_part.lower() in str(col).lower():
                    return row[col]
            return None

        def clean_list(value):
            if not value or pd.isna(value) or str(value).lower() == 'n/a':
                return []
            import re
            items = re.split(r'[,\n]', str(value))
            return [i.strip() for i in items if i.strip()]

        roles_raw = safe_get("Indicate your jobs") or safe_get("Preferred Roles")
        fields_raw = safe_get("Which fields of activity")
        priorities = clean_list(roles_raw)

        return PreferenceData(
            preferred_roles=clean_list(roles_raw),
            top_priorities=priorities[:5],
            salary_expectations=str(safe_get("What are your salary") or ""),
            fields_of_activity=clean_list(fields_raw),
            target_companies=str(safe_get("companies you're particularly interested") or ""),
            application_history=str(safe_get("Where have you already applied") or ""),
            recent_interviews=str(safe_get("Have you had any interviews") or ""),
        )

def load_excel_db(path: str) -> pd.DataFrame:
    return pd.read_excel(path)
