"""Document Intelligence Service — production-grade document analysis router.

Classifies input documents, assesses extraction quality, and routes to the
appropriate extraction pipeline (native text, OCR, or image OCR). Provides
structured diagnostics at every stage so failures are explainable, not silent.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    RTF = "rtf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    NATIVE_TEXT = "native_text"
    OCR_PDF = "ocr_pdf"
    OCR_IMAGE = "ocr_image"
    DOCX_PARSE = "docx_parse"
    TEXT_PARSE = "text_parse"


class DocumentHealth(str, Enum):
    GOOD = "good"
    LOW_TEXT = "low_text"
    SCANNED = "scanned"
    CORRUPTED = "corrupted"
    EMPTY = "empty"
    UNKNOWN = "unknown"


# --- Magic bytes for format detection ---
MAGIC_BYTES = {
    b"%PDF": DocumentFormat.PDF,
    b"PK\x03\x04": DocumentFormat.DOCX,  # ZIP-based (DOCX is ZIP)
    b"\x89PNG": DocumentFormat.PNG,
    b"\xff\xd8\xff": DocumentFormat.JPEG,
}


@dataclass
class DocumentClassification:
    """Result of document type detection."""
    format: DocumentFormat
    mime_type: str | None = None
    is_scanned: bool = False
    has_text_layer: bool = True
    page_count: int = 0
    text_length: int = 0
    health: DocumentHealth = DocumentHealth.UNKNOWN
    recommended_pipeline: ExtractionMethod = ExtractionMethod.NATIVE_TEXT
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class TextQualityReport:
    """Assessment of extracted text quality."""
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0
    avg_line_length: float = 0.0
    garbled_ratio: float = 0.0
    whitespace_ratio: float = 0.0
    has_repeated_whitespace: bool = False
    has_structure: bool = False  # detects newlines, bullets, section headers
    quality_score: float = 0.0  # 0.0 to 1.0
    is_usable: bool = False
    issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(file_path: str | Path, content: bytes | None = None) -> DocumentFormat:
    """Detect document format from extension and magic bytes."""
    path = Path(file_path)
    ext = path.suffix.lower()

    ext_map = {
        ".pdf": DocumentFormat.PDF,
        ".docx": DocumentFormat.DOCX,
        ".doc": DocumentFormat.DOCX,
        ".txt": DocumentFormat.TXT,
        ".html": DocumentFormat.HTML,
        ".htm": DocumentFormat.HTML,
        ".rtf": DocumentFormat.RTF,
        ".png": DocumentFormat.PNG,
        ".jpg": DocumentFormat.JPG,
        ".jpeg": DocumentFormat.JPEG,
        ".webp": DocumentFormat.JPG,  # treat webp like jpg for OCR
    }

    # Check magic bytes first if content available
    if content and len(content) >= 4:
        for magic, fmt in MAGIC_BYTES.items():
            if content[:4] == magic or content[:2] == magic[:2]:
                return fmt

    # Fall back to extension
    return ext_map.get(ext, DocumentFormat.UNKNOWN)


def get_mime_type(fmt: DocumentFormat) -> str:
    """Return MIME type for a document format."""
    mime_map = {
        DocumentFormat.PDF: "application/pdf",
        DocumentFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        DocumentFormat.TXT: "text/plain",
        DocumentFormat.HTML: "text/html",
        DocumentFormat.RTF: "text/rtf",
        DocumentFormat.PNG: "image/png",
        DocumentFormat.JPG: "image/jpeg",
        DocumentFormat.JPEG: "image/jpeg",
    }
    return mime_map.get(fmt, "application/octet-stream")


# ---------------------------------------------------------------------------
# Text quality assessment
# ---------------------------------------------------------------------------

def assess_text_quality(text: str) -> TextQualityReport:
    """Evaluate the quality of extracted text for downstream parsing."""
    report = TextQualityReport()

    if not text or not text.strip():
        report.issues.append("Text is empty or whitespace-only")
        report.quality_score = 0.0
        report.is_usable = False
        return report

    cleaned = text.strip()
    report.char_count = len(cleaned)
    report.word_count = len(cleaned.split())
    report.line_count = len(cleaned.split("\n"))

    if report.line_count > 0:
        lines = [l for l in cleaned.split("\n") if l.strip()]
        report.avg_line_length = sum(len(l) for l in lines) / max(len(lines), 1)

    # Garbled character detection: ratio of non-ASCII, non-whitespace chars
    non_ascii = sum(1 for c in cleaned if not c.isascii() and not c.isspace())
    alpha_chars = sum(1 for c in cleaned if c.isalpha() or c.isspace())
    if alpha_chars > 0:
        report.garbled_ratio = non_ascii / alpha_chars

    # Whitespace ratio
    whitespace = sum(1 for c in cleaned if c.isspace())
    report.whitespace_ratio = whitespace / max(report.char_count, 1)

    # Repeated whitespace check
    report.has_repeated_whitespace = bool(re.search(r"(\s)\1{3,}", cleaned))

    # Structure detection: newlines, bullets, numbered lists, section-like caps
    has_newlines = "\n" in cleaned
    has_bullets = bool(re.search(r"[•\-\*→▶–]", cleaned))
    has_numbered = bool(re.search(r"^\d+[.)]\s", cleaned, re.MULTILINE))
    has_caps_headers = bool(re.search(r"^[A-Z][A-Z\s]{3,}$", cleaned, re.MULTILINE))
    report.has_structure = has_newlines or has_bullets or has_numbered or has_caps_headers

    # Quality scoring
    score = 0.0

    # Word count contribution (resumes typically have 200-2000 words)
    if report.word_count >= 50:
        score += 0.3
    elif report.word_count >= 20:
        score += 0.15
    elif report.word_count >= 5:
        score += 0.05

    # Garbled character penalty
    if report.garbled_ratio < 0.05:
        score += 0.25
    elif report.garbled_ratio < 0.15:
        score += 0.1
    else:
        score -= 0.2

    # Structure bonus
    if report.has_structure:
        score += 0.2

    # Whitespace penalty
    if report.whitespace_ratio < 0.3:
        score += 0.15
    elif report.whitespace_ratio > 0.6:
        score -= 0.1

    # Line length sanity
    if 20 < report.avg_line_length < 200:
        score += 0.1

    # Repeated whitespace penalty
    if report.has_repeated_whitespace:
        score -= 0.1

    report.quality_score = max(0.0, min(1.0, score))
    report.is_usable = report.quality_score >= 0.3 and report.word_count >= 5

    if report.word_count < 5:
        report.issues.append("Very few words extracted")
    if report.garbled_ratio > 0.15:
        report.issues.append("High ratio of garbled/unreadable characters")
    if report.has_repeated_whitespace:
        report.issues.append("Repeated whitespace patterns detected")
    if not report.has_structure:
        report.issues.append("No structural markers (bullets, headers, newlines)")

    return report


# ---------------------------------------------------------------------------
# PDF analysis
# ---------------------------------------------------------------------------

def analyze_pdf(file_path: str | Path) -> DocumentClassification:
    """Analyze a PDF to determine if it has text, is scanned, etc."""
    classification = DocumentClassification(format=DocumentFormat.PDF)

    try:
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            classification.page_count = len(pdf.pages)

            # Sample first 3 pages for text density
            total_chars = 0
            total_images = 0
            pages_with_text = 0

            for i, page in enumerate(pdf.pages[:3]):
                text = page.extract_text() or ""
                total_chars += len(text.strip())
                if text.strip():
                    pages_with_text += 1

                # Count images on page
                if hasattr(page, "images"):
                    total_images += len(page.images)

            classification.text_length = total_chars
            classification.has_text_layer = pages_with_text > 0

            # Determine if scanned
            if total_images > 0 and total_chars < 50:
                classification.is_scanned = True
                classification.diagnostics.append(
                    f"PDF has {total_images} images but only {total_chars} chars on sampled pages"
                )

            # Health assessment
            if total_chars == 0:
                classification.health = DocumentHealth.SCANNED
                classification.recommended_pipeline = ExtractionMethod.OCR_PDF
                classification.diagnostics.append("No extractable text found - likely scanned PDF")
            elif total_chars < 100 and total_images > 0:
                classification.health = DocumentHealth.SCANNED
                classification.recommended_pipeline = ExtractionMethod.OCR_PDF
                classification.diagnostics.append("Very low text with images - using OCR fallback")
            elif total_chars < 50:
                classification.health = DocumentHealth.LOW_TEXT
                classification.diagnostics.append(f"Low text count: {total_chars} chars")
            else:
                classification.health = DocumentHealth.GOOD
                classification.recommended_pipeline = ExtractionMethod.NATIVE_TEXT

    except Exception as exc:
        classification.health = DocumentHealth.CORRUPTED
        classification.diagnostics.append(f"PDF analysis failed: {exc}")
        logger.warning("PDF analysis failed for %s: %s", file_path, exc)

    return classification


# ---------------------------------------------------------------------------
# Document classification (full)
# ---------------------------------------------------------------------------

def classify_document(
    file_path: str | Path,
    content: bytes | None = None,
) -> DocumentClassification:
    """Classify a document and recommend the best extraction pipeline."""
    fmt = detect_format(file_path, content)
    classification = DocumentClassification(format=fmt)
    classification.mime_type = get_mime_type(fmt)

    if fmt == DocumentFormat.PDF:
        return analyze_pdf(file_path)
    elif fmt in (DocumentFormat.DOCX,):
        classification.health = DocumentHealth.GOOD
        classification.recommended_pipeline = ExtractionMethod.DOCX_PARSE
    elif fmt in (DocumentFormat.TXT, DocumentFormat.HTML, DocumentFormat.RTF):
        classification.health = DocumentHealth.GOOD
        classification.recommended_pipeline = ExtractionMethod.TEXT_PARSE
    elif fmt in (DocumentFormat.PNG, DocumentFormat.JPG, DocumentFormat.JPEG):
        classification.health = DocumentHealth.GOOD
        classification.recommended_pipeline = ExtractionMethod.OCR_IMAGE
    else:
        classification.health = DocumentHealth.UNKNOWN
        classification.diagnostics.append(f"Unsupported format: {fmt}")

    return classification
