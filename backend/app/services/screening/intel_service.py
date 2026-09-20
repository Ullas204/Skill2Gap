"""Candidate Evidence Intelligence service (Phase 3 orchestration layer).

Responsibilities:
- Server-side authorization (candidate-level and job-level) before any read.
- Cached per-candidate intelligence, invalidated by a newer resume or an
  engine version change — repeated page loads never recompute or re-call
  the LLM.
- Optional LLM polish of the recruiter-facing summary under the same strict
  JSON contract as Phase 2: only computed facts are sent, any contract
  violation or provider failure keeps the deterministic summary untouched.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.repositories.jobs.job import JobApplicationRepository
from app.repositories.screening.fit import JobFitAnalysisRepository
from app.repositories.screening.intel import CandidateEvidenceIntelRepository
from app.services.screening.access import (
    CandidateNotAccessibleError,
    authorize_candidate_access,
    authorize_job_access,
)
from app.services.screening.fit_service import FitService
from app.services.screening.intel_engine import (
    ENGINE_VERSION,
    build_job_context,
    run_intel_analysis,
)

logger = logging.getLogger(__name__)


class CandidateIntelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.intel_repo = CandidateEvidenceIntelRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.parsed_repo = ParsedResumeDataRepository(session)
        self.app_repo = JobApplicationRepository(session)
        self.profile_repo = CandidateProfileRepository(session)
        self.fit_analysis_repo = JobFitAnalysisRepository(session)

    # ─── profile-level intelligence ────────────────────────────────────

    async def get_intel(self, candidate_id: uuid.UUID, current_user: User) -> dict:
        await authorize_candidate_access(self.session, candidate_id, current_user)

        resume = await self.resume_repo.get_primary(candidate_id)
        parsed = await self.parsed_repo.get_by_resume(resume.id) if resume else None
        profile_json = None
        raw_text = None
        if parsed is not None:
            full_json = parsed.parsed_json or {}
            raw_text = parsed.raw_text
            profile_json = await self._ensure_structured_profile(resume, parsed, full_json)

        existing = await self.intel_repo.get_by_candidate(candidate_id)
        if existing and self._is_fresh(existing, resume):
            return {**existing.result, "cached": True}

        analysis = run_intel_analysis(profile_json, raw_text)

        user = await self.session.get(User, candidate_id)
        result = {
            "candidate_id": str(candidate_id),
            "candidate_name": user.full_name if user else "",
            "resume_id": str(resume.id) if resume else None,
            "engine_version": ENGINE_VERSION,
            **analysis,
            "cached": False,
        }

        polished = await self._polish_summary(result)
        if polished:
            result["summary"]["text"] = polished
            result["summary"]["source"] = "llm_polished"

        payload = {k: v for k, v in result.items() if k != "cached"}
        resume_uuid = resume.id if resume else None  # column type is sa.Uuid
        if existing:
            await self.intel_repo.update(
                existing.id,
                resume_id=resume_uuid,
                engine_version=ENGINE_VERSION,
                result=payload,
            )
        else:
            await self.intel_repo.create(
                candidate_id=candidate_id,
                resume_id=resume_uuid,
                engine_version=ENGINE_VERSION,
                result=payload,
            )
        return result

    # ─── job-contextual intelligence ───────────────────────────────────

    async def get_job_intel(
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

        profile_intel = await self.get_intel(candidate_id, current_user)

        fit_result = None
        existing_fit = await self.fit_analysis_repo.get_by_job_and_candidate(
            job.id, candidate_id,
        )
        if existing_fit is not None and isinstance(existing_fit.result, dict):
            fit_result = {**existing_fit.result}
        if not fit_result:
            # Generate (and cache) via the Phase 2 service when absent.
            fit_service = FitService(self.session)
            try:
                fit_result = await fit_service.get_fit(job_id, candidate_id, current_user)
            except Exception:  # noqa: BLE001 — job context degrades gracefully
                logger.debug("Fit analysis unavailable for job context", exc_info=True)

        context = build_job_context(fit_result) if fit_result else None
        if context is None:
            context = {
                "job_id": str(job.id),
                "job_title": job.title,
                "fit_classification": "insufficient_evidence",
                "fit_score": 0,
                "required_years": None,
                "relevant_years": None,
                "total_years": None,
                "relevance_basis": None,
                "requirement_gaps": [],
                "requirement_unknown": [],
                "additional_questions": [],
                "summary": {
                    "text": (
                        f"Job-specific alignment for '{job.title}' is not available yet. "
                        "Run the evidence-based fit analysis to populate this section."
                    ),
                    "source": "deterministic",
                    "disclaimer": (
                        "AI-assisted evidence analysis based on resume content. "
                        "This is decision support, not a hiring decision."
                    ),
                },
            }

        return {
            "candidate_id": profile_intel["candidate_id"],
            "candidate_name": profile_intel["candidate_name"],
            "job_id": str(job.id),
            "job_title": job.title,
            "engine_version": ENGINE_VERSION,
            "cached": bool(profile_intel.get("cached")),
            "candidate_intelligence": profile_intel,
            "job_context": context,
        }

    # ─── freshness logic ───────────────────────────────────────────────

    async def _ensure_structured_profile(
        self, resume, parsed, full_json: dict,
    ) -> dict | None:
        """Return a structured ``resume_profile`` for this parsed row.

        Rows written by the pre-Phase-1 parser store only the legacy flat
        dict (no ``resume_profile``). When the original file still exists on
        disk we re-parse it ONCE with the current parser and write the
        structured profile back into ``parsed_json`` — self-healing legacy
        data so evidence intelligence gets structured sections instead of
        degrading every skill to raw-text mentions.
        """
        existing = full_json.get("resume_profile")
        if isinstance(existing, dict) and existing:
            return existing

        file_path = getattr(resume, "storage_path", None) if resume else None
        if not file_path or not os.path.isfile(file_path):
            return None

        try:
            from app.services.candidate.resume_parser.engine import (
                ResumeIntelligenceEngine,
            )

            profile, _legacy = ResumeIntelligenceEngine(file_path).parse()
            profile_json = profile.model_dump(mode="json")
            await self.parsed_repo.update(
                parsed.id,
                parsed_json={**full_json, "resume_profile": profile_json},
            )
            logger.info(
                "Backfilled structured resume_profile from stored file (parsed row %s)",
                parsed.id,
            )
            return profile_json
        except Exception:  # noqa: BLE001 — degraded raw-text analysis is still valid
            logger.warning(
                "Could not re-parse resume %s; falling back to raw text",
                getattr(resume, "id", "?"),
                exc_info=True,
            )
            return None

    @staticmethod
    def _is_fresh(existing, resume) -> bool:
        if existing.engine_version != ENGINE_VERSION:
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
        never add evidence. The response MUST be exactly
        ``{"summary": "<rewrite>"}`` — anything else (prose, code fences,
        canned router fallback text) is rejected and the deterministic
        summary survives unchanged.
        """
        snapshot = result.get("snapshot") or {}
        strengths = [s["title"] for s in (result.get("strengths") or [])]
        gaps = [g["skill"] for g in (result.get("evidence_gaps") or [])]
        flags = [(f.get("title"), f.get("severity")) for f in (result.get("review_flags") or [])]
        facts = {
            "total_experience_years": snapshot.get("total_experience_years"),
            "experience_count": snapshot.get("experience_count"),
            "project_count": snapshot.get("project_count"),
            "certification_count": snapshot.get("certification_count"),
            "strongest_evidenced_skills": strengths,
            "skills_without_detailed_evidence": gaps,
            "timeline_observations": flags,
            "deterministic_summary": (result.get("summary") or {}).get("text"),
        }
        system = (
            "You rewrite recruiter-facing candidate evidence summaries for a hiring platform.\n"
            "STRICT RULES:\n"
            "- Respond with ONLY a JSON object: {\"summary\": \"<your rewrite>\"}.\n"
            "- Use ONLY the facts provided in the JSON. Never invent skills, evidence, "
            "dates, certifications or achievements.\n"
            "- Never state that the candidate lacks a skill. When facts list skills "
            "'without detailed evidence', write that no detailed supporting evidence was found.\n"
            "- Never comment on age, gender, family, health, nationality or any personal "
            "characteristics. Evidence about professional skills and history only.\n"
            "- Review flags are neutral observations; never imply dishonesty.\n"
            "- Do not make hiring recommendations. This is decision support only.\n"
            "- Maximum 110 words. Plain professional prose."
        )
        user = (
            "Facts:\n" + json.dumps(facts, indent=2, default=str)
            + "\n\nRewrite this summary using exactly these facts:\n"
            + (result.get("summary") or {}).get("text", "")
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
            cleaned = text
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`").lstrip("json").strip()
            parsed = json.loads(cleaned)
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
        except Exception:  # noqa: BLE001 — LLM failure never breaks the intel result
            logger.debug("LLM summary polish unavailable; keeping deterministic summary")
            return None
