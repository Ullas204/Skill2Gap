"""Text extraction engine — upgraded with OCR fallback, multi-column handling,
table extraction, and quality assessment.

Pipeline:
  file → format detection → native extraction → quality check
  → if insufficient: OCR fallback (scanned PDF / image)
  → multi-column reconstruction
  → table extraction
  → return structured text + metadata
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

logger = logging.getLogger(__name__)

# Minimum usable text length after extraction
MIN_USABLE_CHARS = 20


@dataclass
class ExtractionResult:
    """Structured result from text extraction."""
    text: str
    method: str = "native"
    page_count: int = 0
    tables_found: int = 0
    ocr_used: bool = False
    ocr_confidence: float = 0.0
    char_count: int = 0
    warnings: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)


class TextExtractor:
    SUPPORTED_EXTENSIONS: dict[str, str] = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".html": "text/html",
        ".htm": "text/html",
        ".rtf": "text/rtf",
    }

    @staticmethod
    def extract(file_path: str | Path) -> str:
        """Extract text from a file. Returns plain text string."""
        result = TextExtractor.extract_structured(file_path)
        return result.text

    @staticmethod
    def extract_structured(file_path: str | Path) -> ExtractionResult:
        """Extract text with full metadata and quality info."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            return TextExtractor._extract_pdf_structured(path)
        elif ext == ".docx":
            return TextExtractor._extract_docx_structured(path)
        elif ext in (".html", ".htm"):
            return TextExtractor._extract_html_structured(path)
        elif ext == ".rtf":
            return TextExtractor._extract_rtf_structured(path)
        elif ext == ".txt":
            return TextExtractor._extract_text_structured(path)
        elif ext == ".doc":
            raise ValueError(
                "DOC format (legacy Word) is not supported for direct text extraction. "
                "Please convert to DOCX or PDF."
            )
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    @staticmethod
    def extract_bytes(content: bytes, ext: str) -> str:
        ext = ext.lower()
        if ext == ".pdf":
            return TextExtractor._extract_pdf_bytes(content)
        elif ext == ".docx":
            return TextExtractor._extract_docx_bytes(content)
        elif ext in (".html", ".htm"):
            return TextExtractor._extract_html_bytes(content)
        elif ext == ".rtf":
            return TextExtractor._extract_rtf_bytes(content)
        elif ext == ".txt":
            return content.decode("utf-8", errors="replace")
        elif ext == ".doc":
            raise ValueError("DOC format requires file path for conversion")
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    # ------------------------------------------------------------------
    # PDF extraction with OCR fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_pdf_structured(path: Path) -> ExtractionResult:
        """Extract from PDF with quality check and OCR fallback."""
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDF extraction")

        result = ExtractionResult(text="", method="native_pdf")

        # Phase 1: Try native text extraction
        text_parts: list[str] = []
        tables: list[dict[str, Any]] = []
        page_count = 0

        try:
            with pdfplumber.open(str(path)) as pdf:
                page_count = len(pdf.pages)
                result.page_count = page_count

                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text.strip())

                    # Extract tables
                    try:
                        page_tables = page.extract_tables()
                        for table in page_tables or []:
                            if table and len(table) > 0:
                                # Convert table to structured format
                                headers = [str(h or "") for h in table[0]]
                                rows = []
                                for row in table[1:]:
                                    rows.append([str(cell or "") for cell in row])
                                if any(headers):
                                    tables.append({
                                        "headers": headers,
                                        "rows": rows,
                                        "page": page.page_number,
                                    })
                    except Exception:
                        pass

        except Exception as exc:
            result.warnings.append(f"PDF native extraction failed: {exc}")
            logger.warning("PDF native extraction failed for %s: %s", path, exc)

        # Combine text
        raw_text = "\n".join(text_parts)
        result.char_count = len(raw_text.strip())
        result.tables_found = len(tables)
        result.tables = tables

        # Phase 2: Quality check
        if len(raw_text.strip()) < MIN_USABLE_CHARS:
            result.warnings.append(
                f"Low text yield ({result.char_count} chars) — attempting OCR fallback"
            )

            # Phase 3: OCR fallback
            ocr_text = TextExtractor._try_ocr_fallback(path)
            if ocr_text and len(ocr_text.strip()) > len(raw_text.strip()):
                raw_text = ocr_text
                result.method = "ocr_pdf"
                result.ocr_used = True
                result.char_count = len(ocr_text.strip())
                result.warnings.append("OCR fallback was used for scanned/image PDF")

        # Phase 4: Multi-column reconstruction
        if raw_text.strip():
            raw_text = TextExtractor._reconstruct_reading_order(raw_text)

        # Phase 5: Append table content to text
        if tables:
            raw_text = TextExtractor._append_tables_as_text(raw_text, tables)

        result.text = raw_text.strip()
        return result

    @staticmethod
    def _try_ocr_fallback(path: Path) -> str:
        """Attempt OCR on a PDF that yielded insufficient text."""
        try:
            from app.skill2job.perception.image_ocr import OcrAdapter

            if not OcrAdapter.is_configured():
                logger.info("OCR not configured — skipping OCR fallback")
                return ""

            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context — use sync fallback
                return OcrAdapter.ocr_pdf_sync(str(path))
            else:
                results = loop.run_until_complete(OcrAdapter.ocr_pdf(str(path)))
                return "\n\n".join(r.text for r in results if r.text.strip())
        except Exception as exc:
            logger.warning("OCR fallback failed for %s: %s", path, exc)
            return ""

    @staticmethod
    def _extract_pdf_bytes(content: bytes) -> str:
        if pdfplumber is None:
            raise ImportError("pdfplumber is required for PDF extraction")
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    # ------------------------------------------------------------------
    # DOCX extraction with table support
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_docx_structured(path: Path) -> ExtractionResult:
        """Extract from DOCX including tables."""
        if Document is None:
            raise ImportError("python-docx is required for DOCX extraction")

        result = ExtractionResult(text="", method="docx")
        doc = Document(str(path))

        parts: list[str] = []
        tables: list[dict[str, Any]] = []

        # Extract paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())

        # Extract tables
        for table in doc.tables:
            headers: list[str] = []
            rows: list[list[str]] = []
            for i, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells]
                if i == 0:
                    headers = cells
                else:
                    rows.append(cells)
            if headers:
                tables.append({"headers": headers, "rows": rows})

        raw_text = "\n".join(parts)
        result.char_count = len(raw_text)
        result.tables_found = len(tables)
        result.tables = tables

        # Append tables as text
        if tables:
            raw_text = TextExtractor._append_tables_as_text(raw_text, tables)

        result.text = raw_text.strip()
        return result

    @staticmethod
    def _extract_docx_bytes(content: bytes) -> str:
        if Document is None:
            raise ImportError("python-docx is required for DOCX extraction")
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    # ------------------------------------------------------------------
    # HTML extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_html_structured(path: Path) -> ExtractionResult:
        if BeautifulSoup is None:
            raise ImportError("beautifulsoup4 is required for HTML extraction")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            soup = BeautifulSoup(f.read(), "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        return ExtractionResult(text=text.strip(), method="html")

    @staticmethod
    def _extract_html_bytes(content: bytes) -> str:
        if BeautifulSoup is None:
            raise ImportError("beautifulsoup4 is required for HTML extraction")
        soup = BeautifulSoup(content, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n")

    # ------------------------------------------------------------------
    # RTF extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rtf_structured(path: Path) -> ExtractionResult:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        text = re.sub(r"\\([a-z]+)([-]?\d+)?", " ", content)
        text = re.sub(r"[{}]", "", text)
        text = re.sub(r"\\'[0-9a-f]{2}", "", text)
        text = re.sub(r"\s+", " ", text)
        return ExtractionResult(text=text.strip(), method="rtf")

    @staticmethod
    def _extract_rtf_bytes(content: bytes) -> str:
        text_content = content.decode("utf-8", errors="replace")
        text = re.sub(r"\\([a-z]+)([-]?\d+)?", " ", text_content)
        text = re.sub(r"[{}]", "", text)
        text = re.sub(r"\\'[0-9a-f]{2}", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Plain text extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text_structured(path: Path) -> ExtractionResult:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return ExtractionResult(text=text, method="text")

    # ------------------------------------------------------------------
    # Multi-column reconstruction
    # ------------------------------------------------------------------

    @staticmethod
    def _reconstruct_reading_order(text: str) -> str:
        """Attempt to reconstruct logical reading order from potentially
        multi-column text. Uses layout analysis heuristics."""
        if not text:
            return text

        lines = text.split("\n")
        if len(lines) < 3:
            return text

        # Detect if text likely has columns by checking x-position clustering
        # pdfplumber sometimes concatenates columns inline
        # Heuristic: if many lines have mid-line资本资本资本 (capital letters) patterns
        # or if there are very long lines with content that looks like two columns

        # Simple approach: detect "gap" patterns where two columns are joined
        # by checking if a line has content, a large gap, then more content
        reconstructed: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line might be two columns joined
            # Heuristic: long line with a large internal whitespace gap
            if len(line) > 80:
                # Try splitting on large gaps (3+ spaces or tab)
                parts = re.split(r"\t| {3,}", line)
                if len(parts) >= 2 and all(p.strip() for p in parts):
                    # Looks like multi-column — add each part as separate lines
                    for part in parts:
                        stripped = part.strip()
                        if stripped:
                            reconstructed.append(stripped)
                    i += 1
                    continue

            reconstructed.append(line)
            i += 1

        return "\n".join(reconstructed)

    # ------------------------------------------------------------------
    # Table → text conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _append_tables_as_text(text: str, tables: list[dict[str, Any]]) -> str:
        """Append extracted tables as readable text for downstream parsing."""
        if not tables:
            return text

        table_parts: list[str] = []
        for table in tables:
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            if not headers:
                continue

            # Format as structured text
            lines: list[str] = []
            lines.append(" | ".join(headers))
            lines.append(" | ".join(["---"] * len(headers)))
            for row in rows:
                # Pad row to match header count
                padded = row + [""] * (len(headers) - len(row))
                lines.append(" | ".join(padded[:len(headers)]))
            table_parts.append("\n".join(lines))

        if table_parts:
            text = text + "\n\n" + "\n\n".join(table_parts)

        return text

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def get_mime_type(file_path: str | Path) -> str | None:
        ext = Path(file_path).suffix.lower()
        return TextExtractor.SUPPORTED_EXTENSIONS.get(ext)

    @staticmethod
    def detect_language(text: str) -> str:
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0
            return detect(text[:1000])
        except ImportError:
            pass
        except Exception:
            pass
        english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total = sum(1 for c in text if c.isalpha())
        if total > 0 and (english_chars / total) > 0.8:
            return "en"
        return "unknown"
