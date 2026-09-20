"""Evidence-grounded job fit service (Phase 2 orchestration layer).

Responsibilities:
- Server-side authorization (org isolation) before any data is read.
- Cached job requirement extraction (never re-parse an unchanged JD).
- Cached per (job, candidate) fit analyses, invalidated by job version,
  extractor/engine version or a newer resume.
- Optional LLM polish of the recruiter-facing summary — the deterministic
  result below it must always survive an LLM failure untouched.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.repositories.jobs.job import JobApplicationRepository
from app.repositories.screening.fit import (
    JobFitAnalysisRepository,
    JobRequirementExtractionRepository,
)
from app.services.screening.access import (
    CandidateNotAccessibleError,
    authorize_job_access,
)
from app.services.screening.fit_engine import ENGINE_VERSION, run_fit_analysis
from app.services.screening.requirement_extractor import (
    EXTRACTOR_VERSION,
    JobRequirementExtractor,
)

logger = logging.getLogger(__name__)


class FitService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.extraction_repo = JobRequirementExtractionRepository(session)
        self.fit_repo = JobFitAnalysisRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.parsed_repo = ParsedResumeDataRepository(session)
        self.app_repo = JobApplicationRepository(session)
        self.profile_repo = CandidateProfileRepository(session)

    # ─── public API ────────────────────────────────────────────────────

    async def get_fit(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        job = await authorize_job_access(self.session, job_id, current_user)

        application = await self.app_repo.get_by_job_and_candidate(job.id, candidate_id)
        if not application:
            raise CandidateNotAccessibleError(
                "This candidate has no accessible application for this job"
            )

        resume = await self.resume_repo.get_primary(candidate_id)
        parsed = await self.parsed_repo.get_by_resume(resume.id) if resume else None
        profile_json = None
        raw_text = None
        if parsed is not None:
            full_json = parsed.parsed_json or {}
            profile_json = full_json.get("resume_profile")
            raw_text = parsed.raw_text

        requirements_doc = await self._get_requirements(job)

        existing = await self.fit_repo.get_by_job_and_candidate(job.id, candidate_id)
        if existing and self._is_fresh(existing, requirements_doc, resume, job):
            return {**existing.result, "cached": True}

        analysis = run_fit_analysis(job.title, requirements_doc, profile_json, raw_text)

        user = await self.session.get(User, candidate_id)
        result = {
            "job_id": str(job.id),
            "job_title": job.title,
            "candidate_id": str(candidate_id),
            "candidate_name": user.full_name if user else "",
            "resume_id": str(resume.id) if resume else None,
            **analysis,
            "requirements_info": {
                "extracted_count": (
                    len(requirements_doc.get("required_skills") or [])
                    + len(requirements_doc.get("preferred_skills") or [])
                    + len(requirements_doc.get("responsibilities") or [])
                    + len(requirements_doc.get("certifications") or [])
                    + (1 if requirements_doc.get("education") else 0)
                ),
                "extractor_version": requirements_doc.get(
                    "extractor_version", EXTRACTOR_VERSION,
                ),
            },
            "cached": False,
            "engine_version": ENGINE_VERSION,
        }

        polished = await self._polish_summary(result)
        if polished:
            result["overall"]["summary"] = polished
            result["overall"]["summary_source"] = "llm_polished"

        payload = {k: v for k, v in result.items() if k != "cached"}
        resume_uuid = resume.id if resume else None  # column type is sa.Uuid
        if existing:
            await self.fit_repo.update(
                existing.id,
                resume_id=resume_uuid,
                overall_fit=result["overall"]["classification"],
                fit_score=int(result["overall"]["score"]),
                engine_version=ENGINE_VERSION,
                job_version=job.version or 1,
                result=payload,
            )
        else:
            await self.fit_repo.create(
                job_id=job.id,
                candidate_id=candidate_id,
                resume_id=resume_uuid,
                overall_fit=result["overall"]["classification"],
                fit_score=int(result["overall"]["score"]),
                engine_version=ENGINE_VERSION,
                job_version=job.version or 1,
                result=payload,
            )
        return result

    # ─── requirement extraction cache ──────────────────────────────────

    async def _get_requirements(self, job) -> dict:
        cached = await self.extraction_repo.get_by_job(job.id)
        if (
            cached
            and cached.extractor_version == EXTRACTOR_VERSION
            and cached.job_version >= (job.version or 1)
        ):
            return cached.requirements

        doc = JobRequirementExtractor(job).extract()
        if cached:
            await self.extraction_repo.update(
                cached.id,
                job_version=job.version or 1,
                extractor_version=EXTRACTOR_VERSION,
                requirements=doc,
            )
        else:
            await self.extraction_repo.create(
                job_id=job.id,
                job_version=job.version or 1,
                extractor_version=EXTRACTOR_VERSION,
                requirements=doc,
            )
        return doc

    # ─── freshness logic ───────────────────────────────────────────────

    @staticmethod
    def _is_fresh(existing, requirements_doc: dict, resume, job) -> bool:
        if existing.engine_version != ENGINE_VERSION:
            return False
        if requirements_doc.get("extractor_version") != EXTRACTOR_VERSION:
            return False
        if (existing.job_version or 0) < (job.version or 1):
            return False
        if resume is None:
            return existing.resume_id is None
        if existing.resume_id != resume.id:
            return False
        try:
            if resume.updated_at and existing.updated_at and resume.updated_at > existing.updated_at:
                return False
        except TypeError:  # mixed naive/aware datetimes → be safe, recompute
            return False
        return True

    # ─── optional grounded LLM polish ──────────────────────────────────

    async def _polish_summary(self, result: dict) -> str | None:
        """Rewrite the deterministic summary with the LLM.

        The prompt contains ONLY computed facts; the LLM may rephrase but can
        never add evidence. Any failure returns None and the deterministic
        summary is kept as-is.
        """
        overall = result.get("overall") or {}
        gaps = result.get("skill_gaps") or {}
        facts = {
            "job_title": result.get("job_title"),
            "classification": overall.get("classification"),
            "supported_skills": gaps.get("strengths", []),
            "partial_evidence": gaps.get("partial", []),
            "no_evidence_found_for": gaps.get("gaps", []),
            "insufficient_information_for": gaps.get("unknown", []),
            "experience_reason": (result.get("experience_alignment") or {}).get("reason"),
        }
        system = (
            "You rewrite recruiter-facing fit summaries for a hiring platform.\n"
            "STRICT RULES:\n"
            "- Respond with ONLY a JSON object: {\"summary\": \"<your rewrite>\"}.\n"
            "- Use ONLY the facts provided in the JSON. Never invent skills, "
            "evidence, dates or certifications.\n"
            "- Never state that the candidate lacks a skill. When the facts say "
            "'no_evidence_found_for', write that no supporting evidence was found "
            "in the resume.\n"
            "- Do not make hiring recommendations. This is decision support only.\n"
            "- Maximum 110 words. Plain professional prose."
        )
        import json as _json

        user = (
            "Facts:\n" + _json.dumps(facts, indent=2)
            + "\n\nRewrite this summary using exactly these facts:\n"
            + overall.get("summary", "")
        )
        try:
            from app.ai_core.llm_client import LLMMessage, llm_client

            response = await llm_client.chat(
                [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)],
                temperature=0.1,
                max_tokens=300,
            )
            text = (response.content or "").strip()
            if not text or len(text) > 1500:
                return None
            # The contract is a JSON object {"summary": "..."}. Anything else
            # (prose, code fences, provider fallback messages) is rejected so a
            # canned router response can never replace the real summary.
            cleaned = text
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`").lstrip("json").strip()
            parsed = _json.loads(cleaned)
            summary = parsed.get("summary") if isinstance(parsed, dict) else None
            if not isinstance(summary, str):
                return None
            summary = summary.strip()
            if len(summary) < 10 or len(summary) > 1200:
                return None
            lowered = summary.lower()
            for banned in ("should hire", "recommend hiring", "do not hire"):
                if banned in lowered:
                    return None
            return summary
        except Exception:  # noqa: BLE001 — LLM failure never breaks the fit result
            logger.debug("LLM summary polish unavailable; keeping deterministic summary")
            return None
