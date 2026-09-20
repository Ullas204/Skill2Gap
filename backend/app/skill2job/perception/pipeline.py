"""Perception pipeline orchestrator — upgraded with Document Intelligence routing.

Responsibilities:
- input validation (extension + size gates)
- safe file staging under ``uploads/skill2job``
- document classification and quality assessment
- dispatch to the right extractor (document / free text / voice / image)
- OCR fallback for scanned PDFs and images
- graceful degradation: voice/image without a provider produce a persisted
  ``failed`` result with an honest message, never fabricated text
- partial success: return what was extracted even if some fields fail
- persistence of the provenance-annotated result for later agents
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobPerception
from app.skill2job.perception.document import (
    AUDIO_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    DocumentPerception,
    FreeTextPerception,
    MAX_AUDIO_SIZE,
    MAX_DOCUMENT_SIZE,
    MAX_IMAGE_SIZE,
    StructuredTextPerception,
)
from app.skill2job.perception.document_intelligence import (
    classify_document,
    assess_text_quality,
)
from app.skill2job.perception.free_text import FreeTextParser
from app.skill2job.perception.image_ocr import OcrAdapter, OcrError
from app.skill2job.perception.schemas import PerceptionError, PerceptionResult
from app.skill2job.perception.speech import SpeechToTextError, SpeechTranscriber

logger = logging.getLogger(__name__)

PERCEPTION_VERSION = "skill2job-perception-3.0.0"
PERCEPTION_UPLOAD_DIR = Path(os.getenv("SKILL2JOB_UPLOAD_DIR", "uploads/skill2job"))

ALLOWED_EXTENSIONS = set(DOCUMENT_EXTENSIONS) | set(IMAGE_EXTENSIONS) | set(AUDIO_EXTENSIONS)


class PerceptionValidationError(ValueError):
    pass


class PerceptionPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _validate_upload(filename: str, content: bytes) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise PerceptionValidationError(
                f"Unsupported file type: {ext or '<none>'}. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        if ext in AUDIO_EXTENSIONS:
            limit = MAX_AUDIO_SIZE
        else:
            limit = MAX_IMAGE_SIZE if ext in IMAGE_EXTENSIONS else MAX_DOCUMENT_SIZE
        if len(content) > limit:
            raise PerceptionValidationError(
                f"File size exceeds maximum of {limit // (1024 * 1024)} MB"
            )

    def _stage_file(self, content: bytes, filename: str) -> tuple[str, str]:
        ext = Path(filename).suffix.lower()
        os.makedirs(PERCEPTION_UPLOAD_DIR, exist_ok=True)
        storage_name = f"{uuid.uuid4()}{ext}"
        storage_path = (PERCEPTION_UPLOAD_DIR / storage_name).resolve()
        with open(storage_path, "wb") as f:
            f.write(content)
        return str(storage_path), ext.lstrip(".")

    async def perceive_upload(
        self, user_id: uuid.UUID, filename: str, content: bytes
    ) -> Skill2JobPerception:
        self._validate_upload(filename, content)
        ext = Path(filename).suffix.lower()
        stored_path_str, file_type = self._stage_file(content, filename)

        try:
            if ext in DOCUMENT_EXTENSIONS:
                result = DocumentPerception.perceive(stored_path_str, input_type="document")
            elif ext in IMAGE_EXTENSIONS:
                result = await self._perceive_image(user_id, stored_path_str)
            else:
                result = await self._perceive_audio(user_id, stored_path_str)
        except PerceptionValidationError:
            raise
        except Exception as exc:
            logger.exception("Perception processing failed for %s", filename)
            result = PerceptionResult(
                input_type="document" if ext in DOCUMENT_EXTENSIONS
                else ("image" if ext in IMAGE_EXTENSIONS else "voice"),
                parser_version=PERCEPTION_VERSION,
                processing_status="failed",
                processing_message=str(exc),
                errors=[PerceptionError(
                    code="PROCESSING_FAILED",
                    message=str(exc),
                    stage="processing",
                    recoverable=False,
                )],
                warnings=[],
            )

        return await self._persist(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            content_hash=hashlib.sha256(content).hexdigest(),
            stored_path=stored_path_str,
            result=result,
        )

    async def perceive_text(self, user_id: uuid.UUID, text: str) -> Skill2JobPerception:
        sanitized = FreeTextParser.sanitize(text)
        if not sanitized.strip():
            raise PerceptionValidationError("No text provided for perception")
        try:
            result = FreeTextPerception.perceive(sanitized, input_type="free_text")

            # Enhance with LLM-powered skill extraction (best-effort)
            try:
                from app.skill2job.perception.free_text import FreeTextParser as FTP
                llm_skills = await FTP.extract_skills_with_llm(sanitized)
                if llm_skills and result.skills:
                    existing = {s.lower() for s in result.skills}
                    for skill in llm_skills:
                        if skill.lower() not in existing:
                            result.skills.append(skill)
                            existing.add(skill.lower())
                elif llm_skills and not result.skills:
                    result.skills = llm_skills

                # Also extract structured profile via LLM
                llm_profile = await FTP.extract_structured_profile_with_llm(sanitized)
                if llm_profile:
                    if "location" in llm_profile and llm_profile["location"]:
                        result.source_metadata["llm_location"] = llm_profile["location"]
                    if "education" in llm_profile:
                        result.source_metadata["llm_education"] = llm_profile["education"]
                    if "certifications" in llm_profile:
                        result.source_metadata["llm_certifications"] = llm_profile["certifications"]
            except Exception as llm_exc:
                logger.debug("LLM enhancement of text perception failed: %s", llm_exc)

        except Exception as exc:
            logger.exception("Free-text perception failed")
            result = PerceptionResult(
                input_type="free_text",
                parser_version=PERCEPTION_VERSION,
                extracted_text=sanitized[:2000],
                processing_status="failed",
                processing_message=str(exc),
                errors=[PerceptionError(
                    code="TEXT_PARSING_FAILED",
                    message=str(exc),
                    stage="text_parsing",
                    recoverable=True,
                )],
            )
        return await self._persist(
            user_id=user_id,
            filename=None,
            file_type="txt",
            content_hash=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
            stored_path=None,
            result=result,
        )

    async def _perceive_image(self, user_id: uuid.UUID, stored_path: str) -> PerceptionResult:
        if not OcrAdapter.is_configured():
            raise OcrError(
                "OCR is not configured on this deployment (no ``pytesseract`` + "
                "Tesseract binary). The image was preserved but not transcribed."
            )
        text = await OcrAdapter.ocr(stored_path)
        if not text.strip():
            raise OcrError("OCR produced no readable text from this image")
        result = StructuredTextPerception.perceive(text, input_type="image")
        result.source_metadata["method"] = "ocr"
        result.source_metadata["providers"] = OcrAdapter.available_providers()
        return result

    async def _perceive_audio(self, user_id: uuid.UUID, stored_path: str) -> PerceptionResult:
        if not SpeechTranscriber.is_configured():
            raise SpeechToTextError(
                "Speech-to-text is not configured on this deployment. No provider "
                "is available (install ``openai`` + set OPENAI_API_KEY)."
            )
        text = await SpeechTranscriber.transcribe(stored_path)
        if not text.strip():
            raise SpeechToTextError("Transcription produced no text")
        result = StructuredTextPerception.perceive(text, input_type="voice")
        result.source_metadata["method"] = "stt"
        result.source_metadata["providers"] = SpeechTranscriber.available_providers()
        return result

    async def _persist(
        self,
        *,
        user_id: uuid.UUID,
        filename: str | None,
        file_type: str | None,
        content_hash: str,
        stored_path: str | None,
        result: PerceptionResult,
    ) -> Skill2JobPerception:
        record = Skill2JobPerception(
            user_id=user_id,
            input_type=result.input_type,
            original_filename=filename,
            file_type=file_type,
            file_size=0,
            stored_path=stored_path,
            processing_status=result.processing_status,
            processing_message=result.processing_message,
            extracted_text=result.extracted_text,
            result=result.model_dump(mode="json"),
            warnings=result.warnings,
            parser_version=result.parser_version,
        )
        self.session.add(record)
        await self.session.flush()
        return record
