"""Document perception — upgraded with Document Intelligence routing.

Reuses the existing Resume Intelligence Engine for core parsing, but wraps it
with:
- Document classification and quality assessment
- OCR fallback for scanned PDFs
- Multi-column text reconstruction
- Table extraction
- Structured error reporting
- Partial success handling (return what was extracted even if some fields fail)
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.skill2job.perception.document_intelligence import (
    DocumentFormat,
    ExtractionMethod,
    classify_document,
    assess_text_quality,
)
from app.skill2job.perception.free_text import FreeTextParser
from app.services.candidate.resume_parser.engine import ResumeIntelligenceEngine, PARSER_VERSION
from app.services.candidate.resume_parser.schemas import ResumeProfile
from app.services.candidate.resume_parser.text_extractor import TextExtractor

from app.skill2job.perception.schemas import (
    DocumentInfo,
    PerceptionCertification,
    PerceptionEducation,
    PerceptionError,
    PerceptionExperience,
    PerceptionLanguage,
    PerceptionProject,
    PerceptionResult,
    PerceptionSkill,
    ParsingQuality,
    Provenance,
)

logger = logging.getLogger(__name__)

DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".html", ".htm", ".rtf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
MAX_AUDIO_SIZE = 20 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024


class DocumentPerception:
    """Structured perception from a resume/CV/text document with intelligence routing."""

    SUPPORTED_EXTENSIONS = set(DOCUMENT_EXTENSIONS)

    @staticmethod
    def extract_text(file_path: str | Path) -> str:
        return TextExtractor.extract(file_path)

    @staticmethod
    def perceive(file_path: str | Path, input_type: str = "document") -> PerceptionResult:
        """Parse a document with full intelligence routing and quality assessment."""
        path = Path(file_path)
        errors: list[PerceptionError] = []
        warnings: list[str] = []

        # Step 1: Classify document
        classification = classify_document(path)
        doc_info = DocumentInfo(
            type="resume",
            format=classification.format.value,
            pages=classification.page_count or None,
            is_scanned=classification.is_scanned,
            extraction_method=classification.recommended_pipeline.value,
        )

        # Step 2: Extract text with structured result
        extraction_result = TextExtractor.extract_structured(path)
        raw_text = extraction_result.text
        doc_info.ocr_used = extraction_result.ocr_used
        doc_info.tables_found = extraction_result.tables_found
        doc_info.extraction_method = extraction_result.method

        # Step 3: Assess text quality
        quality_report = assess_text_quality(raw_text)

        # Step 4: If text is unusable and OCR wasn't tried, report it
        if not quality_report.is_usable and not extraction_result.ocr_used:
            errors.append(PerceptionError(
                code="TEXT_EXTRACTION_INSUFFICIENT",
                message="Could not extract sufficient text from the document. "
                        "The document may be scanned, encrypted, or contain only images.",
                stage="text_extraction",
                recoverable=True,
            ))

        # Step 5: Parse with Resume Intelligence Engine
        profile = None
        if raw_text.strip():
            try:
                # Write to temp file for engine (engine expects file path)
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(
                    "w", suffix=".txt", delete=False, encoding="utf-8"
                ) as f:
                    f.write(raw_text)
                    tmp_path = f.name

                try:
                    engine = ResumeIntelligenceEngine(tmp_path)
                    profile, _parsed = engine.parse()
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

            except ValueError as exc:
                # Engine returned no text — this is expected for empty docs
                errors.append(PerceptionError(
                    code="PARSER_EMPTY",
                    message=str(exc),
                    stage="parsing",
                    recoverable=True,
                ))
            except Exception as exc:
                logger.exception("Resume intelligence engine failed for %s", path)
                errors.append(PerceptionError(
                    code="PARSER_FAILED",
                    message=f"Parsing failed: {exc}",
                    stage="parsing",
                    recoverable=True,
                ))
                warnings.append(f"Engine error: {exc}")

        # Step 6: Build result from profile (even partial)
        if profile:
            result = _Mapper(profile, input_type, engine_name=PARSER_VERSION).to_result()
        else:
            # Create a minimal result with whatever we have
            result = PerceptionResult(
                input_type=input_type,
                parser_version=PARSER_VERSION,
                extracted_text=raw_text[:5000] if raw_text else None,
                processing_status="partial" if raw_text else "failed",
                processing_message="Limited information could be extracted" if raw_text else "No text could be extracted",
            )

        # Step 7: Merge extraction metadata
        result.document = doc_info
        result.errors = errors
        result.warnings = list(set(result.warnings + warnings + extraction_result.warnings))
        result.extracted_text = raw_text[:5000] if raw_text else result.extracted_text

        # Step 8: Calculate quality metrics
        result.quality = ParsingQuality(
            text_quality=quality_report.quality_score,
            layout_quality=0.8 if extraction_result.method != "ocr_pdf" else 0.6,
            entity_quality=_calculate_entity_quality(result),
            overall_confidence=result.field_confidence,
        )

        # Step 9: Update processing status
        if result.skills or result.experience or result.education:
            if result.errors:
                result.processing_status = "partial"
            else:
                result.processing_status = "ok"
        elif raw_text:
            result.processing_status = "partial"
            result.processing_message = "Text was extracted but no structured information could be parsed"
        else:
            result.processing_status = "failed"

        return result


def _calculate_entity_quality(result: PerceptionResult) -> float:
    """Calculate quality of extracted entities."""
    score = 0.0
    total_fields = 0

    if result.skills:
        score += min(len(result.skills) / 5, 1.0) * 0.3
        total_fields += 0.3
    if result.experience:
        score += min(len(result.experience) / 2, 1.0) * 0.25
        total_fields += 0.25
    if result.education:
        score += min(len(result.education) / 1, 1.0) * 0.2
        total_fields += 0.2
    if result.summary:
        score += 0.15
        total_fields += 0.15
    if result.projects:
        score += min(len(result.projects) / 2, 1.0) * 0.1
        total_fields += 0.1

    return round(score / max(total_fields, 0.01), 3)


class _Mapper:
    """Maps a ``ResumeProfile`` to a provenance-annotated ``PerceptionResult``."""

    def __init__(self, profile: ResumeProfile, input_type: str, engine_name: str) -> None:
        self.profile = profile
        self.input_type = input_type
        self.engine_name = engine_name

    def _provenance(self, *, section: str, evidence: str | None = None, confidence: float = 1.0) -> Provenance:
        return Provenance(
            source=self.input_type,
            section=section,
            evidence=evidence,
            confidence=confidence,
            method=self.engine_name,
        )

    def to_result(self) -> PerceptionResult:
        profile = self.profile
        prov = self._provenance

        skills: list[PerceptionSkill] = []
        for skill in profile.skills:
            skills.append(
                PerceptionSkill(
                    name=skill.name,
                    canonical=skill.name,
                    category=skill.category,
                    inferred=skill.inferred,
                    provenance=prov(
                        section="skills",
                        evidence=skill.source_text,
                        confidence=0.95 if not skill.inferred else 0.6,
                    ),
                )
            )

        education: list[PerceptionEducation] = []
        for entry in profile.education:
            education.append(
                PerceptionEducation(
                    institution=entry.institution,
                    degree=entry.degree,
                    field_of_study=entry.field_of_study,
                    start_date=entry.start_date,
                    end_date=entry.end_date,
                    raw_text=entry.raw_text,
                    provenance=prov(section="education", evidence=entry.raw_text),
                )
            )

        experience: list[PerceptionExperience] = []
        for entry in profile.experience:
            experience.append(
                PerceptionExperience(
                    company=entry.company,
                    job_title=entry.job_title or entry.title,
                    location=entry.location,
                    start_date=entry.start_date,
                    end_date=entry.end_date,
                    is_current=entry.is_current,
                    duration_months=entry.duration_months,
                    description=entry.description or entry.responsibilities,
                    technologies=entry.technologies,
                    provenance=prov(section="experience", evidence=entry.source_text),
                )
            )

        projects: list[PerceptionProject] = []
        for entry in profile.projects:
            projects.append(
                PerceptionProject(
                    name=entry.name,
                    description=entry.description,
                    technologies=entry.technologies,
                    provenance=prov(section="projects", evidence=entry.source_text),
                )
            )

        certifications: list[PerceptionCertification] = []
        for entry in profile.certifications:
            certifications.append(
                PerceptionCertification(
                    name=entry.name,
                    issuer=entry.issuer,
                    date=entry.date,
                    provenance=prov(section="certifications"),
                )
            )

        languages: list[PerceptionLanguage] = []
        for entry in profile.languages:
            languages.append(
                PerceptionLanguage(
                    language=entry.language,
                    proficiency=entry.proficiency,
                    provenance=prov(section="languages"),
                )
            )

        personal_info = profile.personal_info or {}
        raw_location = personal_info.get("location")
        if isinstance(raw_location, dict):
            location = raw_location.get("city") or raw_location.get("formatted")
        elif isinstance(raw_location, str):
            location = raw_location.split(",")[0].strip() if raw_location else None
        else:
            location = None

        interests: list[str] = []
        targets: list[str] = []

        result = PerceptionResult(
            input_type=self.input_type,
            parser_version=self.engine_name,
            summary=profile.summary,
            skills=skills,
            education=education,
            experience=experience,
            projects=projects,
            certifications=certifications,
            languages=languages,
            interests=interests,
            target_roles=targets,
            location=location,
            source_metadata={
                "language": profile.metadata.language,
                "detected_sections": [
                    s.section for s in profile.metadata.detected_sections
                ],
                "provenance": [
                    prov(
                        section=s.section,
                        evidence=s.heading,
                        confidence=s.confidence,
                    ).model_dump()
                    for s in profile.metadata.detected_sections
                ],
            },
        )
        result.provenance = [
            prov(
                section=s.section,
                evidence=s.heading,
                confidence=s.confidence,
            )
            for s in profile.metadata.detected_sections
        ]
        result.field_confidence = PerceptionConfidence.score(result)
        return result


class PerceptionConfidence:
    """Deterministic fill-rate confidence for a perception result."""

    _FIELDS = (
        ("skills", 0.25, lambda r: bool(r.skills)),
        ("experience", 0.15, lambda r: bool(r.experience)),
        ("summary", 0.10, lambda r: bool(r.summary)),
        ("education", 0.10, lambda r: bool(r.education)),
        ("projects", 0.10, lambda r: bool(r.projects)),
        ("certifications", 0.10, lambda r: bool(r.certifications)),
        ("languages", 0.10, lambda r: bool(r.languages)),
        ("location", 0.10, lambda r: bool(r.location)),
    )

    @classmethod
    def score(cls, result: PerceptionResult) -> float:
        total = 0.0
        for _name, weight, is_present in cls._FIELDS:
            if is_present(result):
                total += weight
        return round(total, 3)


class FreeTextPerception:
    """Perception from pasted free text using the same Resume engine.

    Text is written to a temp ``.txt`` file and parsed with the shared, proven
    resume intelligence pipeline so the free-text path yields the same quality
    and provenance as a resume upload.
    """

    @staticmethod
    def perceive(text: str, input_type: str = "free_text") -> PerceptionResult:
        raw = FreeTextParser.sanitize(text)
        if not raw.strip():
            raise ValueError("No text provided for perception")

        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(raw)
            tmp_path = f.name

        try:
            engine = ResumeIntelligenceEngine(tmp_path)
            profile, _parsed = engine.parse()
            result = _Mapper(profile, input_type, engine_name=PARSER_VERSION).to_result()
            result.source_metadata["method"] = "free_text"
        finally:
            import os

            try:
                os.remove(tmp_path)
            except OSError:
                pass

        FreeTextPerception._merge_signals(result, raw)

        # Assess text quality
        quality_report = assess_text_quality(raw)
        result.quality = ParsingQuality(
            text_quality=quality_report.quality_score,
            layout_quality=1.0,
            entity_quality=_calculate_entity_quality(result),
            overall_confidence=result.field_confidence,
        )

        if not result.skills and not result.experience:
            result.processing_status = "partial"
            result.processing_message = "Limited structured information could be extracted from the text."
        return result

    @staticmethod
    def _merge_signals(result: PerceptionResult, raw: str) -> None:
        """Merge conservative pattern-grounded signals into the parse result."""
        roles = FreeTextParser.extract_target_roles(raw)
        location = FreeTextParser.extract_location(raw)
        interests = FreeTextParser.extract_interests(raw)
        years = FreeTextParser.extract_experience_years(raw)

        FreeTextPerception._merge_dictionary_skills(result, raw)

        if roles and not result.target_roles:
            result.target_roles = roles
        if location and not result.location:
            result.location = location
        if interests and not result.interests:
            result.interests = interests
        if years is not None:
            result.source_metadata["stated_experience_years"] = years

        if not any(p.source == result.input_type for p in result.provenance):
            result.provenance.append(
                Provenance(
                    source=result.input_type,
                    section="text",
                    confidence=0.8,
                    method="resume-intelligence-engine + pattern scan",
                )
            )

    @staticmethod
    def _merge_dictionary_skills(result: PerceptionResult, raw: str) -> None:
        """Backfill skills the structured engine missed using the shared
        dictionary scan (deterministic, word-boundary aware, no invented skills).
        """
        from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer

        existing = {s.canonical.lower() if s.canonical else s.name.lower() for s in result.skills}
        prov = Provenance(
            source=result.input_type,
            section="text",
            confidence=0.9,
            method="skill-dictionary-scan",
        )
        for skill in SkillNormalizer.extract_from_text(raw):
            key = skill.name.lower()
            if key in existing:
                continue
            existing.add(key)
            result.skills.append(
                PerceptionSkill(
                    name=skill.name,
                    canonical=skill.name,
                    category=skill.category,
                    inferred=False,
                    provenance=prov,
                )
            )


class StructuredTextPerception:
    """Structured perception from an already-extracted text blob (e.g. OCR/STT)."""

    @staticmethod
    def perceive(text: str, input_type: str) -> PerceptionResult:
        return FreeTextPerception.perceive(text, input_type)
