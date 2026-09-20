"""Intelligent section detection for resumes.

Upgrades the legacy regex-only ``SectionParser`` with:
- expanded synonym tables ("Professional Background" -> experience,
  "Technical Expertise" -> skills, ...)
- multi-line headers ("WORK" / "EXPERIENCE" on consecutive lines)
- fuzzy matching via ``difflib`` (no external dependencies)
- per-section confidence scores and traceability metadata
- deterministic behaviour, no LLM calls

The legacy ``SectionParser`` remains untouched and importable; this module is
a strict superset used by the new pipeline.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .schemas import DetectedSectionInfo

# Canonical section -> known heading phrases (matched case-insensitively,
# full-line after decoration stripping).
HEADER_PHRASES: dict[str, list[str]] = {
    "summary": [
        "professional summary", "summary", "profile", "profile summary",
        "about me", "about", "career summary", "executive summary",
        "overview", "professional overview",
    ],
    "objective": [
        "objective", "career objective", "professional objective", "career goals",
    ],
    "experience": [
        "work experience", "professional experience", "experience", "employment history",
        "employment", "work history", "career history", "professional background",
        "relevant experience", "industry experience", "internship experience",
        "work & experience", "experiences",
    ],
    "education": [
        "education", "academic background", "educational background", "academics",
        "academic qualifications", "qualifications", "education & training",
        "academic history", "studies", "degrees", "educational qualifications",
    ],
    "skills": [
        "skills", "technical skills", "core competencies", "competencies", "key skills",
        "skill set", "areas of expertise", "areas of specialization", "expertise",
        "technical expertise", "technologies", "tech stack", "technical proficiencies",
        "it skills", "tools & technologies", "proficiencies", "technical proficiencies",
        "skills & expertise", "core skills", "professional skills",
    ],
    "projects": [
        "projects", "key projects", "selected projects", "personal projects",
        "academic projects", "side projects", "project experience", "portfolio",
        "notable projects",
    ],
    "certifications": [
        "certifications", "certificates", "certification", "licenses", "credentials",
        "licenses & certifications", "training & certifications", "professional development",
    ],
    "languages": [
        "languages", "language proficiency", "foreign languages", "spoken languages",
    ],
    "achievements": [
        "achievements", "awards", "honors", "honours", "awards & honors",
        "recognition", "accomplishments", "achievements & awards",
    ],
    "publications": ["publications", "papers", "research papers", "research", "patents"],
    "references": ["references", "professional references", "referees"],
    "interests": [
        "interests", "hobbies", "hobbies & interests", "activities",
        "extracurricular activities", "volunteer experience",
    ],
    "personal_info": [
        "contact", "contact information", "contact details", "personal information",
        "personal details",
    ],
}

# Flat phrase -> canonical table for fast exact matching.
_PHRASE_TO_SECTION: dict[str, str] = {}
for _canon, _phrases in HEADER_PHRASES.items():
    for _phrase in _phrases:
        _PHRASE_TO_SECTION.setdefault(_phrase.lower(), _canon)

# Decorative characters commonly wrapped around headings.
_DECORATION_RE = re.compile(r"^[\s#*•\-=_+~|>\[\]().,;:!?]+|[\s#*•\-=_+~|\[\]().,;:!?]+$")
_LEADING_NUMBERING_RE = re.compile(r"^(?:\(?\d{1,2}\)?[.)\\/-]?\s+)(?=\S)")
_BULLET_PREFIX_RE = re.compile(r"^[\s]*[•\-*>→▶–‣⁃○▪▸▹►➢➤・]+")

MAX_HEADER_LEN = 60
MIN_FUZZY_RATIO = 0.88


class IntelligentSectionParser:
    """Detects resume sections with synonyms, fuzzy matching and confidence."""

    @staticmethod
    def normalize_heading(line: str) -> str | None:
        """Normalize a raw line into a heading candidate, or None."""
        cleaned = _BULLET_PREFIX_RE.sub("", line.strip())
        cleaned = cleaned.strip()
        cleaned = _DECORATION_RE.sub("", cleaned).strip()
        cleaned = _LEADING_NUMBERING_RE.sub("", cleaned).strip()
        cleaned = cleaned.rstrip(":").strip()
        if not cleaned:
            return None
        return cleaned

    @staticmethod
    def _is_header_candidate(normalized: str | None) -> bool:
        if not normalized:
            return False
        if len(normalized) > MAX_HEADER_LEN:
            return False
        words = normalized.split()
        if not 1 <= len(words) <= 8:
            return False
        if normalized.endswith((".", "?", "!")):
            return False
        if "@" in normalized or re.search(r"https?://|www\.", normalized, re.IGNORECASE):
            return False
        if re.search(r"\d{4}", normalized):  # year-bearing lines are content
            return False
        if not re.search(r"[A-Za-z]", normalized):
            return False
        return True

    @classmethod
    def classify_heading(cls, normalized: str) -> tuple[str, float] | None:
        """Return (canonical_section, confidence) for a normalized heading."""
        key = re.sub(r"\s+", " ", normalized).strip().lower()
        if not key:
            return None

        # 1. Exact phrase match.
        if key in _PHRASE_TO_SECTION:
            return _PHRASE_TO_SECTION[key], 0.98

        # 2. Plural/singular tolerant exact match.
        singular = key[:-1] if key.endswith("s") else f"{key}s"
        if singular in _PHRASE_TO_SECTION:
            return _PHRASE_TO_SECTION[singular], 0.95

        # 2b. Compound heading: head phrase + descriptor tail
        #     ("Certifications and Work Readiness", "Skills & Interests").
        compound = re.split(r"\s+(?:and|&|with)\s+", key)
        if len(compound) == 2 and compound[0] in _PHRASE_TO_SECTION:
            return _PHRASE_TO_SECTION[compound[0]], 0.88

        # 3. Substring: heading is a phrase plus small filler
        #    ("My Technical Skills", "Summary of Qualifications").
        #    Guardrails: everything outside the phrase must be tiny filler
        #    (connectors / <=2 chars), and the phrase must cover >=50% of the
        #    line -- otherwise content sentences containing a section word
        #    would falsely match.
        connectors = {"my", "our", "the", "of", "&", "and", "in", "for", "a", "an"}
        best: tuple[str, float] | None = None
        for phrase, canon in _PHRASE_TO_SECTION.items():
            if phrase not in key or len(key) - len(phrase) > 20:
                continue
            prefix, _, suffix = key.partition(phrase)
            outside = re.findall(r"[a-z&]+", f"{prefix} {suffix}")
            if any(t not in connectors and len(t) > 2 for t in outside):
                continue
            if len(phrase) < 0.5 * len(key):
                continue
            conf = 0.85
            if best is None or conf > best[1]:
                best = (canon, conf)
        if best:
            return best

        # 4. Fuzzy match against all phrases (typos, OCR-ish variants).
        best_ratio = 0.0
        best_canon: str | None = None
        for phrase, canon in _PHRASE_TO_SECTION.items():
            if abs(len(key) - len(phrase)) > max(len(key), len(phrase)) * 0.45:
                continue
            ratio = SequenceMatcher(None, key, phrase).ratio()
            if ratio > best_ratio:
                best_ratio, best_canon = ratio, canon
        if best_canon is not None and best_ratio >= MIN_FUZZY_RATIO:
            confidence = min(0.60 + (best_ratio - MIN_FUZZY_RATIO) * 1.5, 0.90)
            return best_canon, round(confidence, 2)
        return None

    @staticmethod
    def _warn_worthy(normalized: str, original_line: str) -> bool:
        """Only report unrecognized headings that look like real headings:
        Title Case / UPPER, 2+ words, and not a bare known skill token."""
        words = normalized.split()
        if len(words) < 2:
            from app.services.candidate.resume_parser.skill_database import SKILL_LOOKUP

            if normalized.lower() in SKILL_LOOKUP:
                return False
        styled = original_line.strip().rstrip(":")
        looks_like_heading = styled.isupper() or styled.istitle() or all(
            w[:1].isupper() for w in words if w[:1].isalpha()
        )
        return looks_like_heading

    @classmethod
    def detect(
        cls, text: str
    ) -> tuple[dict[str, str], list[DetectedSectionInfo], list[str]]:
        """Split resume text into sections.

        Returns ``(sections, detected_infos, warnings)`` where *sections* maps
        canonical section names to their body text (headers excluded).
        """
        lines = text.split("\n")
        sections: dict[str, list[str]] = {}
        detected: list[DetectedSectionInfo] = []
        warnings: list[str] = []

        current = "__preamble__"
        sections[current] = []
        last_content_idx: dict[str, int] = {"__preamble__": -1}

        i = 0
        n = len(lines)
        while i < n:
            raw_line = lines[i]
            stripped = raw_line.strip()

            if stripped:
                normalized = cls.normalize_heading(stripped)
                if cls._is_header_candidate(normalized):
                    classified = cls.classify_heading(normalized or "")

                    # Multi-line header: "WORK" followed by "EXPERIENCE".
                    if classified is None and i + 1 < n:
                        next_norm = cls.normalize_heading(lines[i + 1])
                        if next_norm and len(normalized or "") <= 30:
                            joined = f"{normalized} {next_norm}"
                            joined_cls = cls.classify_heading(joined)
                            if joined_cls:
                                # Consume both lines as the heading.
                                cls._maybe_retract_last_content(
                                    sections, current, last_content_idx
                                )
                                current = joined_cls[0]
                                detected.append(
                                    DetectedSectionInfo(
                                        section=current,
                                        heading=f"{normalized} {next_norm}",
                                        confidence=joined_cls[1],
                                    )
                                )
                                sections.setdefault(current, [])
                                last_content_idx[current] = len(sections[current]) - 1
                                i += 2
                                continue

                    if classified:
                        current = classified[0]
                        detected.append(
                            DetectedSectionInfo(
                                section=current, heading=normalized or "", confidence=classified[1]
                            )
                        )
                        sections.setdefault(current, [])
                        last_content_idx[current] = len(sections[current]) - 1
                        i += 1
                        continue

                    if normalized and cls._warn_worthy(normalized, stripped):
                        warnings.append(f"Unrecognized possible section heading: '{normalized}'")

            if stripped:
                sections.setdefault(current, []).append(stripped)
                last_content_idx[current] = len(sections[current]) - 1
            i += 1

        body = {
            name: "\n".join(content).strip()
            for name, content in sections.items()
            if content and "\n".join(content).strip()
        }
        return body, detected, warnings

    @staticmethod
    def _maybe_retract_last_content(
        sections: dict[str, list[str]], current: str, last_content_idx: dict[str, int]
    ) -> None:
        """Remove the immediately-preceding content line if it was likely the
        first half of a two-line heading."""
        idx = last_content_idx.get(current, -1)
        content = sections.get(current)
        if content and idx == len(content) - 1 and idx >= 0:
            candidate = content[idx]
            normalized = IntelligentSectionParser.normalize_heading(candidate)
            if (
                normalized
                and len(normalized) <= 30
                and not re.search(r"[,;.]", normalized)
                and not _BULLET_PREFIX_RE.search(candidate)
            ):
                content.pop()


# Convenience wrapper keeping the legacy call signature.
def detect_sections_intelligent(text: str) -> dict[str, str]:
    sections, _, _ = IntelligentSectionParser.detect(text)
    return sections
