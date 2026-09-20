"""Free-text parsing helpers (Phase 2 + LLM).

The structured extraction itself is delegated to the shared Resume
Intelligence Engine (see ``document.py``). This module only:
- sanitizes pasted text (encoding, whiskers),
- performs conservative, pattern-grounded signal extraction (location,
  target roles, interests, years of experience) that the structured pipeline
  does not cover,
- provides LLM-powered skill extraction for richer, context-aware parsing.

Conservativeness rule: a signal is only captured when the text explicitly
states it (e.g. "looking for <role>"), never guessed.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

_ROLE_LIST = {
    "developer": "Software Developer",
    "engineer": "Engineer",
    "software engineer": "Software Engineer",
    "frontend developer": "Frontend Developer",
    "front-end developer": "Frontend Developer",
    "backend developer": "Backend Developer",
    "back-end developer": "Backend Developer",
    "full stack developer": "Full Stack Developer",
    "fullstack developer": "Full Stack Developer",
    "full-stack developer": "Full Stack Developer",
    "data scientist": "Data Scientist",
    "data analyst": "Data Analyst",
    "data engineer": "Data Engineer",
    "ml engineer": "ML Engineer",
    "machine learning engineer": "ML Engineer",
    "ai engineer": "AI Engineer",
    "devops engineer": "DevOps Engineer",
    "solution architect": "Solution Architect",
    "product manager": "Product Manager",
    "project manager": "Project Manager",
    "ux designer": "UX Designer",
    "ui designer": "UI Designer",
    "qa engineer": "QA Engineer",
    "test engineer": "Test Engineer",
    "security engineer": "Security Engineer",
    "cloud engineer": "Cloud Engineer",
    "technical writer": "Technical Writer",
    "competitive programmer": "Competitive Programmer",
    "blockchain developer": "Blockchain Developer",
    "mobile developer": "Mobile Developer",
    "android developer": "Android Developer",
    "ios developer": "iOS Developer",
}

# Matches "I am a <role>", "worked as <role>", "seeking/looking for <role>".
_TARGET_ROLE_RE = re.compile(
    r"\b(?:seeking|looking for|targeting|aspiring to be|aiming to be|apply to be)"
    r"(?:\s+a|\s+an|\s+the)?\s+(.+?)(?:\.|,|;|\n|$)",
    re.IGNORECASE,
)
_CURRENT_ROLE_RE = re.compile(
    r"\b(?:i\s+am|i'm|i\s+work\s+as|worked\s+as|currently\s+working\s+as)\s+"
    r"(?:a|an|the)?\s*([A-Za-z][\w/+# .-]{2,50})\b",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"\b(?:based in|located in|currently in|from)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){0,2})",
    re.IGNORECASE,
)
_INTERESTS_RE = re.compile(
    r"\b(?:interests?|passionate about|i enjoy|love)\s*[::\-]?\s*(.+?)[\.,;]",
    re.IGNORECASE,
)
_EXPERIENCE_RE = re.compile(
    r"\b(\d{1,2})\+?\s*(?:\+|to|–|-|\s)?\s*years?\s*(?:of\s+)?(?:experience|exp)\b",
    re.IGNORECASE,
)


class FreeTextParser:
    @staticmethod
    def sanitize(text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def extract_target_roles(text: str) -> list[str]:
        roles: list[str] = []
        for match in _TARGET_ROLE_RE.finditer(text):
            candidate = match.group(1).strip().lower()
            for phrase, canonical in sorted(_ROLE_LIST.items(), key=lambda kv: -len(kv[0])):
                if phrase in candidate:
                    if canonical not in roles:
                        roles.append(canonical)
                    break
        return roles

    @staticmethod
    def extract_location(text: str) -> str | None:
        match = _LOCATION_RE.search(text)
        if not match:
            return None
        candidate = match.group(1).strip()
        return candidate if candidate and len(candidate) > 2 else None

    @staticmethod
    def extract_interests(text: str) -> list[str]:
        interests: list[str] = []
        for match in _INTERESTS_RE.finditer(text):
            raw = match.group(1).strip()
            for token in re.split(r"[,;]|\band\b", raw):
                token = token.strip()
                if 3 <= len(token) <= 40 and token not in interests:
                    interests.append(token)
        return interests[:8]

    @staticmethod
    def extract_experience_years(text: str) -> int | None:
        match = _EXPERIENCE_RE.search(text)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, TypeError):
                return None
        return None

    # ─── LLM-powered extraction ──────────────────────────────────────────

    @staticmethod
    async def extract_skills_with_llm(text: str) -> list[str]:
        """Use LLM to extract a comprehensive list of skills from free text.

        Falls back to an empty list if LLM is unavailable. This method is
        designed to complement (not replace) the deterministic extraction
        already provided by the Resume Intelligence Engine.
        """
        if not text or len(text.strip()) < 20:
            return []
        try:
            from app.ai_core.llm_client import LLMClient, LLMMessage

            client = LLMClient()
            prompt = (
                "You are a technical skill extractor. Extract ALL technical skills, "
                "tools, frameworks, programming languages, and technologies mentioned "
                "or implied in the following text. Return a JSON array of skill names "
                "(lowercase, deduplicated). Only include real, specific technical skills "
                "(e.g., 'python', 'react', 'aws', 'sql', 'docker') — not soft skills "
                "like 'communication' or 'leadership'.\n\n"
                f"Text:\n{text[:2000]}\n\n"
                "Return ONLY the JSON array, no explanation."
            )
            response = await client.chat(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.2,
                max_tokens=512,
            )
            if response.content:
                cleaned = response.content.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                skills = json.loads(cleaned)
                if isinstance(skills, list):
                    return [str(s).lower().strip() for s in skills if isinstance(s, str)][:30]
        except Exception as exc:
            logger.debug("LLM skill extraction failed (falling back to deterministic): %s", exc)
        return []

    @staticmethod
    async def extract_structured_profile_with_llm(text: str) -> dict:
        """Use LLM to extract a structured profile from free text.

        Returns a dict with keys: skills, target_roles, location, interests,
        experience_years, education, certifications. Missing fields are omitted.
        Falls back to an empty dict if LLM is unavailable.
        """
        if not text or len(text.strip()) < 20:
            return {}
        try:
            from app.ai_core.llm_client import LLMClient, LLMMessage

            client = LLMClient()
            prompt = (
                "You are a resume/profile parser. Extract structured information "
                "from the following text. Return a JSON object with these keys "
                "(omit any that are not found):\n"
                '- "skills": array of technical skills (lowercase)\n'
                '- "target_roles": array of job titles they are seeking\n'
                '- "location": string (city)\n'
                '- "interests": array of interest areas\n'
                '- "experience_years": integer or null\n'
                '- "education": array of degrees/qualifications\n'
                '- "certifications": array of professional certifications\n\n'
                f"Text:\n{text[:2000]}\n\n"
                "Return ONLY the JSON object, no explanation."
            )
            response = await client.chat(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.2,
                max_tokens=600,
            )
            if response.content:
                cleaned = response.content.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                profile = json.loads(cleaned)
                if isinstance(profile, dict):
                    return profile
        except Exception as exc:
            logger.debug("LLM profile extraction failed (falling back to deterministic): %s", exc)
        return {}