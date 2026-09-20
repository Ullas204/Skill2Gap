"""Job requirement extraction (Phase 2, Feature 1).

Turns an existing Job row into structured requirements:

    JOB ROW (structured columns + free-text description)
        ↓
    deterministic parsing
        ↓
    {required_skills, preferred_skills, minimum experience,
     education, certifications, responsibilities}

Rules:
- Only requirements supported by the job data are extracted. Nothing invented.
- Skill normalization reuses the Phase 1 ``SkillNormalizer`` (shared dictionary;
  no second normalization source).
- Extraction is cached per job (see ``JobRequirementExtraction``), so repeated
  page loads never re-parse the same description.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.models import Job
from app.services.candidate.resume_parser.skill_normalizer import (
    NormalizedSkill,
    SkillNormalizer,
)

EXTRACTOR_VERSION = "jre-1.0.0"

# Sentence-level qualifiers that decide the required vs preferred bucket.
_PREFERRED_RE = re.compile(
    r"\b(preferred|nice\s+to\s+have|plus|bonus|desirable|familiarity|familiar\s+with)\b",
    re.IGNORECASE,
)
_REQUIRED_RE = re.compile(
    r"\b(required|must(?:\s+have)?|minimum|min\.?|strong|solid|proficien\w*|expert|"
    r"hands[-\s]on|experience\s+(?:with|using|in)|years?\s+of\s+experience)\b",
    re.IGNORECASE,
)
_SECTION_HEADING_RE = re.compile(
    r"^(?:requirements|qualifications|what\s+you.?ll\s+need|skills\s+(?:and|&)\s+"
    r"experience|must[-\s]haves?)\b",
    re.IGNORECASE,
)
_RESPONSIBILITY_HEADING_RE = re.compile(
    r"^(?:responsibilit(?:ies|y)|what\s+you.?ll\s+do|the\s+role|about\s+the\s+role|"
    r"duties|key\s+responsibilities)\b",
    re.IGNORECASE,
)
_EXPERIENCE_YEARS_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:(?:to|-)\s*(\d+(?:\.\d+)?)\s*)?years?\b",
    re.IGNORECASE,
)
_EDUCATION_DEGREE_RE = re.compile(
    r"\b(bachelor(?:'s)?|master(?:'s)?|b\.?tech|b\.?e\b|b\.?sc|m\.?tech|m\.?sc|mba|"
    r"phd|doctorate|associate(?:'s)?|diploma)\b",
    re.IGNORECASE,
)
_CERTIFICATION_MARKERS_RE = re.compile(
    r"\b(certif(?:ied|ication|icate)s?|cka|ckad|pmp|csm|aws\s+certified|"
    r"azure\s+certified|gcp\s+certified)\b",
    re.IGNORECASE,
)
_ACTION_VERB_RE = re.compile(
    r"^(?:build|design|develop|lead|manage|own|drive|create|deliver|maintain|"
    r"implement|collaborate|mentor|architect|optimize|automate|ship|scale|write|"
    r"define|improve|support|partner|work)\b",
    re.IGNORECASE,
)
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-•*‣▪]|\d+[.)])\s+")

_MAX_RESPONSIBILITIES = 6


def _split_statements(text: str) -> list[tuple[str, str]]:
    """Split a description into (statement, section_context) tuples.

    ``section_context`` is "requirements" or "responsibilities" when the
    statement appears under such a heading, otherwise "".
    """
    statements: list[tuple[str, str]] = []
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        stripped = _BULLET_PREFIX_RE.sub("", line).strip()
        clean_heading = stripped.rstrip(": ").strip()
        if len(clean_heading) < 60:
            if _SECTION_HEADING_RE.match(clean_heading):
                section = "requirements"
                continue
            if _RESPONSIBILITY_HEADING_RE.match(clean_heading):
                section = "responsibilities"
                continue
        for sentence in re.split(r"(?<=[.;!?])\s+(?=[A-Z0-9])", stripped):
            sentence = sentence.strip()
            if len(sentence) >= 3:
                statements.append((sentence, section))
    return statements


class JobRequirementExtractor:
    """Deterministic extractor; no LLM calls, no invention."""

    def __init__(self, job: Job) -> None:
        self.job = job

    def extract(self) -> dict[str, Any]:
        structured_required = SkillNormalizer.normalize_list(
            self._as_str_list(self.job.required_skills)
        )
        structured_preferred = SkillNormalizer.normalize_list(
            self._as_str_list(self.job.preferred_skills)
        )

        statements = _split_statements(self.job.description or "")
        desc_required, desc_preferred, desc_neutral, quotes = self._extract_skills(statements)
        responsibilities = self._extract_responsibilities(statements)
        min_years, experience_note = self._extract_experience(statements)
        education = self._extract_education(statements)
        certifications = self._extract_certifications(statements)

        required = self._merge_buckets(structured_required, desc_required)
        preferred = self._merge_buckets(structured_preferred, desc_preferred, exclude=required)

        # If nothing anywhere signals a hard requirement, plain technology
        # mentions are treated as required rather than silently dropped.
        # Explicitly "preferred" wording always stays preferred.
        if not required:
            required = self._merge_buckets([], desc_neutral)

        # Structured column wins for experience/education; description parsing
        # only fills gaps.
        min_years_structured = _parse_years_from_string(self.job.experience_required)
        if min_years_structured is not None:
            min_years = max(min_years or 0.0, min_years_structured)

        return {
            "extractor_version": EXTRACTOR_VERSION,
            "required_skills": [self._dump(s) for s in required],
            "preferred_skills": [self._dump(s) for s in preferred],
            "minimum_experience_years": min_years,
            "experience_note": self.job.experience_required or experience_note,
            "education": self.job.education_required or education,
            "certifications": certifications,
            "responsibilities": responsibilities,
            "skill_source_quotes": quotes,
        }

    # ─── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _dump(skill: NormalizedSkill) -> dict[str, Any]:
        return skill.model_dump(mode="json")

    @staticmethod
    def _as_str_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v) for v in value if v]
        return []

    @staticmethod
    def _bucket_for(statement: str, section: str) -> str | None:
        if _PREFERRED_RE.search(statement):
            return "preferred"
        if _REQUIRED_RE.search(statement):
            return "required"
        if section == "requirements":
            return "required"
        return None

    @staticmethod
    def _extract_skills(
        statements: list[tuple[str, str]],
    ) -> tuple[list[NormalizedSkill], list[NormalizedSkill], list[NormalizedSkill], dict[str, str]]:
        required: list[NormalizedSkill] = []
        preferred: list[NormalizedSkill] = []
        neutral: list[NormalizedSkill] = []
        quotes: dict[str, str] = {}
        for statement, section in statements:
            found = SkillNormalizer.extract_from_text(statement)
            if not found:
                continue
            bucket = JobRequirementExtractor._bucket_for(statement, section)
            for skill in found:
                quotes.setdefault(skill.name.lower(), statement[:300])
                if bucket == "preferred":
                    preferred.append(skill)
                elif bucket == "required":
                    required.append(skill)
                else:
                    neutral.append(skill)
        return required, preferred, neutral, quotes

    @staticmethod
    def _merge_buckets(
        primary: list[NormalizedSkill],
        extra: list[NormalizedSkill],
        exclude: list[NormalizedSkill] | None = None,
    ) -> list[NormalizedSkill]:
        blocked = {s.name.lower() for s in (exclude or [])}
        return SkillNormalizer.merge(primary, [
            s for s in extra if s.name.lower() not in blocked
        ])

    @staticmethod
    def _extract_experience(
        statements: list[tuple[str, str]],
    ) -> tuple[float | None, str | None]:
        best: float | None = None
        note: str | None = None
        for statement, _section in statements:
            match = _EXPERIENCE_YEARS_RE.search(statement)
            if not match:
                continue
            years = float(match.group(1))
            # "3-5 years" / "3 to 5 years" → lower bound is the minimum.
            if best is None or years > best:
                best = years
                note = statement[:200]
        return best, note

    @staticmethod
    def _extract_education(statements: list[tuple[str, str]]) -> str | None:
        for statement, _section in statements:
            if _EDUCATION_DEGREE_RE.search(statement):
                return statement[:200]
        return None

    @staticmethod
    def _extract_certifications(statements: list[tuple[str, str]]) -> list[str]:
        certs: list[str] = []
        for statement, _section in statements:
            if _CERTIFICATION_MARKERS_RE.search(statement):
                trimmed = statement.strip()
                if trimmed and trimmed.lower() not in {c.lower() for c in certs}:
                    certs.append(trimmed[:200])
        return certs

    @staticmethod
    def _extract_responsibilities(statements: list[tuple[str, str]]) -> list[str]:
        duties: list[str] = []
        for statement, section in statements:
            if section == "responsibilities" or (
                _ACTION_VERB_RE.match(statement) and len(statement.split()) >= 4
            ):
                cleaned = statement.strip().rstrip(".")
                if cleaned and cleaned.lower() not in {d.lower() for d in duties}:
                    duties.append(cleaned[:250])
            if len(duties) >= _MAX_RESPONSIBILITIES:
                break
        return duties


def _parse_years_from_string(text: str | None) -> float | None:
    """Parse a minimum-years value out of an experience string like '4+ years'."""
    if not text:
        return None
    match = _EXPERIENCE_YEARS_RE.search(text)
    return float(match.group(1)) if match else None
