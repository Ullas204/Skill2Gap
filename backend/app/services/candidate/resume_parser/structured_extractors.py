"""Structured entity extraction for the Resume Intelligence Engine (Phase 1).

Upgrades the legacy ``entity_extractors`` with:
- robust multi-format experience blocks (title/company/location/employment type,
  ISO-normalized dates, durations)
- achievement vs responsibility classification for bullets
- per-role technology detection (reusing the existing skill dictionary)
- richer project entries
- deterministic rules only; nothing is invented

Legacy classes remain untouched; these v2 classes wrap/reuse them where their
output is already solid (education, certifications, languages).
"""

from __future__ import annotations

import re
from typing import Any

from .date_utils import (
    compute_duration_months,
    format_duration,
    parse_date_range,
    parse_single_date,
)
from .schemas import (
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    ProjectEntry,
)
from .section_parser import SectionParser
from .skill_matcher import SkillMatcher
from .skill_normalizer import SkillNormalizer, normalize_display
from .entity_extractors import (
    CertificationExtractor,
    LanguageExtractor,
)

BULLET_RE = re.compile(r"^[\s]*(?:[•\-*>→▶–‣⁃○▪▸▹►➢➤・]+|\d{1,2}[.)])\s+")

QUANTIFIED_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%|\$\s?\d[\d,.]*\s*(?:[kmbn]\b|illion)?|\b\d+(?:\.\d+)?\s*(?:k|m|x)\b)",
    re.IGNORECASE,
)
RESULT_PHRASES_RE = re.compile(
    r"(?:result(?:ing|ed)?\s+in|led\s+to|leading\s+to|as\s+a\s+result)", re.IGNORECASE
)
ACHIEVEMENT_VERBS_RE = re.compile(
    r"\b(?:increased|decreased|reduced|improved|grew|boosted|saved|generated|"
    r"delivered|launched|achieved|exceeded|optimized|streamlined|accelerated|"
    r"doubled|tripled|scaled|automated|migrated|consolidated|won|awarded|"
    r"recognized|promoted)\b",
    re.IGNORECASE,
)

EMPLOYMENT_TYPES: dict[str, str] = {
    "internship": "Internship",
    "intern": "Internship",
    "part-time": "Part-time",
    "part time": "Part-time",
    "full-time": "Full-Time",
    "full time": "Full-Time",
    "contract": "Contract",
    "contractor": "Contract",
    "freelance": "Freelance",
    "freelancer": "Freelance",
    "temporary": "Temporary",
    "temp": "Temporary",
    "volunteer": "Volunteer",
}

COMPANY_SUFFIXES = [
    "inc", "inc.", "llc", "ltd", "ltd.", "llp", "corp", "corp.", "corporation",
    "company", "co", "co.", "technologies", "technology", "tech", "labs",
    "lab", "systems", "solutions", "group", "studio", "studios", "media",
    "software", "digital", "ventures", "capital", "partners", "consulting",
    "university", "college", "institute", "school", "bank", "agency",
]

LOCATION_INLINE_RE = re.compile(
    r"\b(?:remote|hybrid|on[- ]?site)\b", re.IGNORECASE
)
LOCATION_STATE_RE = re.compile(r",\s*[A-Z]{2}\b(?:,\s*USA)?\s*$")

SEPARATOR_SPLIT_RE = re.compile(r"\s*[|•·—–]| @ |,(?=\s)|\s+-\s+")


def classify_line(text: str) -> str:
    """Classify a bullet as ``achievement`` or ``responsibility``."""
    if QUANTIFIED_RE.search(text):
        return "achievement"
    if RESULT_PHRASES_RE.search(text):
        return "achievement"
    # Verb markers need quantification OR an outcome phrase to count;
    # strong action verbs alone with numbers also qualify.
    if ACHIEVEMENT_VERBS_RE.search(text) and re.search(r"\d", text):
        return "achievement"
    return "responsibility"


def _is_bullet(line: str) -> bool:
    return bool(BULLET_RE.match(line))


def _strip_bullet(line: str) -> str:
    return BULLET_RE.sub("", line).strip()


ABBREVIATION_ENDINGS = {
    "inc.", "ltd.", "llc.", "corp.", "co.", "jr.", "sr.", "st.", "dr.", "mr.",
    "mrs.", "ms.", "vs.", "etc.",
}


def _looks_like_header_line(line: str) -> bool:
    if len(line) > 110 or len(line.split()) > 16:
        return False
    if line.endswith((".", "?", "!")):
        last_token = line.rstrip().split()[-1].lower()
        abbreviation_ok = last_token in ABBREVIATION_ENDINGS
        has_explicit_separator = bool(re.search(r"[|•·—–]| @ ", line))
        if not (abbreviation_ok or has_explicit_separator):
            return False
    return True


def _detect_technologies(block_text: str) -> list[str]:
    """Detect known skills mentioned in *block_text*, display-normalized."""
    out: list[str] = []
    seen: set[str] = set()
    for skill in SkillMatcher.extract_skills(block_text):
        db_category = skill.get("category")
        if db_category == "soft_skills":
            continue
        display = normalize_display(str(skill["name"]).lower())
        if display.lower() not in seen:
            seen.add(display.lower())
            out.append(display)
    return out


def _extract_employment_type(text: str) -> str | None:
    lower = text.lower()
    for token, label in EMPLOYMENT_TYPES.items():
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return label
    return None


class ExperienceExtractorV2:
    """Extracts structured, dated work-experience entries."""

    @classmethod
    def extract(cls, section_text: str) -> list[ExperienceEntry]:
        blocks = cls._split_into_entries(section_text)
        entries: list[ExperienceEntry] = []
        for block in blocks:
            entry = cls._parse_entry(block)
            if entry.job_title or entry.company:
                entries.append(entry)
        return entries

    @staticmethod
    def _split_into_entries(text: str) -> list[list[str]]:
        lines_raw = text.split("\n")
        blocks: list[list[str]] = []
        current: list[str] = []
        blank_run = False

        def flush() -> None:
            nonlocal current
            if current:
                blocks.append(current)
                current = []

        def entry_is_complete(entry_lines: list[str]) -> bool:
            has_bullets = any(_is_bullet(l) for l in entry_lines)
            has_dates = any(parse_date_range(l)[0] or parse_date_range(l)[1] for l in entry_lines)
            return bool(entry_lines) and has_bullets and has_dates

        for raw in lines_raw:
            line = raw.rstrip()
            if not line.strip():
                blank_run = True
                continue

            if (
                blank_run
                and current
                and entry_is_complete(current)
                and not _is_bullet(line)
                and _looks_like_header_line(line)
            ):
                flush()
            blank_run = False

            if _is_bullet(line):
                current.append(line)
                continue

            start_dv, end_dv, _ = parse_date_range(line)
            has_new_date = start_dv is not None or end_dv is not None
            current_has_dates = any(parse_date_range(l)[0] or parse_date_range(l)[1] for l in current)

            if has_new_date and current_has_dates:
                # A second date range means a previous entry just ended.
                flush()
            elif (
                not has_new_date
                and _looks_like_header_line(line)
                and entry_is_complete(current)
            ):
                # Compact format: the previous entry already has dates and
                # bullets, so this non-bullet line starts the next one.
                flush()
            current.append(line)

        flush()
        return blocks

    @classmethod
    def _parse_entry(cls, block_lines: list[str]) -> ExperienceEntry:
        header_lines: list[str] = []
        date_lines: list[str] = []
        bullets: list[str] = []
        prose: list[str] = []

        for line in block_lines:
            if _is_bullet(line):
                bullets.append(_strip_bullet(line))
                continue
            start_dv, end_dv, _ = parse_date_range(line)
            if start_dv or end_dv:
                date_lines.append(line)
            elif _looks_like_header_line(line) and len(header_lines) < 5:
                header_lines.append(line)
            else:
                prose.append(line)

        # ---- Dates -------------------------------------------------------
        start_dv = end_dv = None
        is_current = False
        for dl in date_lines:
            s, e, cur = parse_date_range(dl)
            if s or e:
                start_dv, end_dv, is_current = s, e, cur
                break

        duration_months = compute_duration_months(start_dv, end_dv, is_current)
        dates_uncertain = bool(
            (start_dv is not None and start_dv.uncertain)
            or (end_dv is not None and end_dv.uncertain)
            or start_dv is None
        )

        # ---- Title / company / location ----------------------------------
        job_title, company, location = cls._split_header(header_lines)
        if not job_title and not company and header_lines:
            job_title = header_lines[0][:120]
        employment_type = _extract_employment_type(" ".join([*header_lines, *date_lines]))

        # ---- Bullets -----------------------------------------------------
        responsibilities = [b for b in bullets if classify_line(b) == "responsibility"]
        achievements = [b for b in bullets if classify_line(b) == "achievement"]

        block_text = "\n".join([*header_lines, *prose, *bullets])
        technologies = _detect_technologies(block_text)

        source_text = " | ".join(header_lines)[:200] if header_lines else None

        return ExperienceEntry(
            company=company,
            job_title=job_title,
            title=job_title,
            location=location,
            employment_type=employment_type,
            start_date=start_dv.iso if start_dv else None,
            end_date=end_dv.iso if end_dv else None,
            original_start_date=start_dv.original if start_dv else None,
            original_end_date=end_dv.original if end_dv else None,
            is_current=is_current,
            dates_uncertain=dates_uncertain,
            duration_months=duration_months,
            duration_label=format_duration(duration_months),
            description=[*prose, *bullets],
            responsibilities=responsibilities,
            achievements=achievements,
            technologies=technologies,
            source_section="experience",
            source_text=source_text,
        )

    @staticmethod
    def _split_header(
        header_lines: list[str],
    ) -> tuple[str | None, str | None, str | None]:
        if not header_lines:
            return None, None, None

        best_parts: list[str] = []
        for line in header_lines:
            parts = [p.strip(" ,\t") for p in SEPARATOR_SPLIT_RE.split(line) if p and p.strip(" ,\t")]
            if len(parts) > len(best_parts):
                best_parts = parts

        if not best_parts:
            return None, None, None

        location: str | None = None
        employment_free_parts: list[str] = []
        for part in best_parts:
            if LOCATION_INLINE_RE.fullmatch(part.strip()) or LOCATION_STATE_RE.search(part):
                location = part.strip()
            else:
                employment_free_parts.append(part)

        def has_company_suffix(part: str) -> bool:
            tail = part.rstrip(". ").split()[-1].lower() if part.split() else ""
            return tail in COMPANY_SUFFIXES

        company: str | None = None
        title_parts: list[str] = []
        for idx, part in enumerate(employment_free_parts):
            if company is None and (has_company_suffix(part) or "@" in part or idx > 0):
                company = part
            else:
                title_parts.append(part)

        job_title = " - ".join(title_parts)[:150] if title_parts else None
        return job_title, company, location


PROJECT_ACTION_VERB_RE = re.compile(
    r"^(?:developed|built|created|designed|implemented|engineered|programmed|coded|"
    r"worked|led|managed)\b",
    re.IGNORECASE,
)


class ProjectExtractorV2:
    """Extracts project entries with technologies and achievement tagging."""

    TECH_LINE_RE = re.compile(
        r"^(?:technologies|tech stack|tools|built with|stack|skills)\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    )

    @classmethod
    def extract(cls, section_text: str) -> list[ProjectEntry]:
        blocks = cls._split_into_projects(section_text)
        entries: list[ProjectEntry] = []
        for block in blocks:
            entry = cls._parse_project(block)
            # Keep nameless entries only when they carry real content.
            if entry.name or entry.description or entry.technologies:
                entries.append(entry)
        return entries

    @classmethod
    def _split_into_projects(cls, text: str) -> list[list[str]]:
        blocks: list[list[str]] = []
        current: list[str] = []
        saw_bullet = False

        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            # A "Technologies: ..." line always continues the current project.
            if cls.TECH_LINE_RE.match(line):
                current.append(line)
                saw_bullet = True
                continue
            if _is_bullet(line):
                current.append(line)
                saw_bullet = True
                continue
            if saw_bullet and _looks_like_header_line(line):
                # Non-bullet line after bullets starts the next project.
                if current:
                    blocks.append(current)
                current = [line]
                saw_bullet = False
            else:
                if current and saw_bullet:
                    blocks.append(current)
                    current = [line]
                    saw_bullet = False
                else:
                    current.append(line)
        if current:
            blocks.append(current)
        return blocks

    @classmethod
    def _parse_project(cls, block_lines: list[str]) -> ProjectEntry:
        name: str | None = None
        description: list[str] = []
        tech_explicit: list[str] = []
        date_text_lines: list[str] = []
        extra_header: list[str] = []

        for line in block_lines:
            if _is_bullet(line):
                description.append(_strip_bullet(line))
                continue
            tech_match = cls.TECH_LINE_RE.match(line)
            if tech_match:
                tech_explicit.extend(t.strip() for t in re.split(r"[,;|]", tech_match.group(1)) if t.strip())
                continue
            s, e, _ = parse_date_range(line)
            if s or e:
                date_text_lines.append(line)
                continue
            if name is None and _looks_like_header_line(line):
                if PROJECT_ACTION_VERB_RE.match(line):
                    # Description sentence, not a project title.
                    description.append(line)
                    continue
                name = re.sub(r"^\(?\d{1,2}\)?[.)\\/-]?\s*", "", line).strip()[:150]
            elif PROJECT_ACTION_VERB_RE.match(line) and not parse_date_range(line)[0]:
                description.append(line)
                continue
            else:
                extra_header.append(line)

        start_dv, end_dv = None, None
        for dl in [*extra_header, *date_text_lines]:
            s, e, _ = parse_date_range(dl)
            if s or e:
                start_dv, end_dv = s, e
                break

        block_text = "\n".join([*extra_header, *description])
        technologies = list(tech_explicit)
        seen_tech = {t.lower() for t in technologies}
        for tech in _detect_technologies(block_text):
            if tech.lower() not in seen_tech:
                seen_tech.add(tech.lower())
                technologies.append(tech)

        responsibilities = [b for b in description if classify_line(b) == "responsibility"]
        achievements = [b for b in description if classify_line(b) == "achievement"]

        return ProjectEntry(
            name=name,
            description=description,
            technologies=technologies,
            responsibilities=responsibilities,
            achievements=achievements,
            start_date=start_dv.iso if start_dv else None,
            end_date=end_dv.iso if end_dv else None,
            source_section="projects",
            source_text=(name or None),
        )


class EducationMapper:
    """Extracts education entries with normalized dates.

    Deliberately does NOT delegate degree detection to the legacy
    ``EducationExtractor``, whose alternation-ordered regex truncates degrees
    (e.g. ``Master of ...`` -> ``"Ma"``). Institution/GPA patterns are reused.
    """

    DEGREE_LINE_RE = re.compile(
        r"\b(bachelor(?:'s)?|master(?:'s)?|associate(?:'s)?|doctorate|ph\.?d\.?|"
        r"mba|m\.?b\.?a\.?|bba|b\.?tech|m\.?tech|b\.?e\b|m\.?e\b|b\.?sc|m\.?sc|"
        r"b\.?com|m\.?com|bca|mca|diploma|high\s*school)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _split_blocks(text: str) -> list[list[str]]:
        blocks: list[list[str]] = []
        current: list[str] = []
        for raw in text.split("\n"):
            line = raw.strip()
            if _is_bullet(line):
                line = _strip_bullet(line)
            if not line:
                if current:
                    blocks.append(current)
                    current = []
            else:
                current.append(line)
        if current:
            blocks.append(current)
        return blocks

    @staticmethod
    def _trim_dates(line: str) -> str:
        """Remove inline date tokens ("Nov 2024", "2026", 01/2025") from a line."""
        from .date_utils import MONTH_YEAR_RE, NUMERIC_MONTH_YEAR_RE, PRESENT_WORDS

        date_token_re = re.compile(
            rf"(?:{MONTH_YEAR_RE.pattern})|(?:{NUMERIC_MONTH_YEAR_RE.pattern})"
            rf"|\b(?:19|20)\d{{2}}\b|{PRESENT_WORDS}",
            re.IGNORECASE,
        )
        trimmed = date_token_re.sub(" ", line)
        trimmed = re.sub(r"\s{2,}", " ", trimmed)
        trimmed = re.sub(r"^[\s,–—-]+|[\s,]*[-–—]?[\s,]*$", "", trimmed)
        # A separator left dangling between two removed dates.
        trimmed = re.sub(r"\s+[-–—]\s*$", "", trimmed)
        return trimmed.strip()

    @classmethod
    def _split_degree_and_institution(cls, line: str) -> tuple[str | None, str | None]:
        """Handle combined lines: "MCA - Sapthagiri NPS University (2024-2026)"."""
        from app.services.candidate.resume_parser.entity_extractors import (
            EducationExtractor,
        )

        has_degree = bool(cls.DEGREE_LINE_RE.search(line))
        has_institution = bool(EducationExtractor.INSTITUTION_PATTERNS.search(line))
        if not (has_degree and has_institution):
            return None, None

        parts = [p.strip(" -–—") for p in re.split(r"[|,:@]|\s+-\s+|\s+–\s+", line) if p.strip()]
        degree = institution = None
        for part in parts:
            if EducationExtractor.INSTITUTION_PATTERNS.search(part) and institution is None:
                institution = part
            elif cls.DEGREE_LINE_RE.search(part) and degree is None and len(part) <= 90:
                degree = part
        return degree, institution

    @classmethod
    def extract(cls, section_text: str) -> list[EducationEntry]:
        from app.services.candidate.resume_parser.entity_extractors import (
            EducationExtractor,
        )

        entries: list[EducationEntry] = []

        for block in cls._split_blocks(section_text):
            degree_line: str | None = None
            institution_line: str | None = None
            gpa: str | None = None

            for line in block:
                if "gpa" in line.lower() or "cgpa" in line.lower():
                    m = re.search(
                        r"(?:GPA|CGPA|grade\s*point)\s*:?\s*(\d+\.?\d*)", line, re.IGNORECASE
                    )
                    if m:
                        gpa = m.group(1)
                    continue
                s_dv, e_dv, _ = parse_date_range(line)
                if (s_dv or e_dv) and len(line) <= 40:
                    continue  # pure date line
                combined_degree, combined_institution = cls._split_degree_and_institution(
                    line
                )
                if combined_degree or combined_institution:
                    if degree_line is None and combined_degree:
                        degree_line = combined_degree
                    if institution_line is None and combined_institution:
                        institution_line = combined_institution
                    continue
                if (
                    degree_line is None
                    and cls.DEGREE_LINE_RE.search(line)
                    and len(line) <= 90
                ):
                    degree_line = line
                elif institution_line is None and len(line) <= 120:
                    if EducationExtractor.INSTITUTION_PATTERNS.search(line):
                        institution_line = line

            # Fallback: institution embedded in the degree line ("B.Tech, IIT Delhi").
            if institution_line is None and degree_line:
                parts = [p.strip() for p in degree_line.split(",")]
                if len(parts) > 1 and EducationExtractor.INSTITUTION_PATTERNS.search(parts[-1]):
                    institution_line = parts[-1]
                    degree_line = ", ".join(parts[:-1])

            if not (degree_line or institution_line):
                continue

            # Strip any date ranges that got glued onto the heading lines.
            if degree_line:
                degree_line = cls._trim_dates(degree_line)
            if institution_line:
                institution_line = cls._trim_dates(institution_line)

            start_iso = end_iso = None
            start_orig = end_orig = None
            for line in block:
                s_dv, e_dv, _ = parse_date_range(line)
                if s_dv or e_dv:
                    start_orig, end_orig = (s_dv.original if s_dv else None), (e_dv.original if e_dv else None)
                    start_iso, end_iso = (s_dv.iso if s_dv else None), (e_dv.iso if e_dv else None)
                    break

            field = cls._extract_field("\n".join(block))
            raw_text = "\n".join(block)

            entries.append(
                EducationEntry(
                    institution=institution_line,
                    degree=(degree_line[:150] if degree_line else None),
                    field_of_study=field,
                    start_date=start_iso,
                    end_date=end_iso,
                    original_start_date=start_orig,
                    original_end_date=end_orig,
                    gpa=gpa,
                    raw_text=raw_text[:300],
                    source_section="education",
                )
            )
        return entries

    @staticmethod
    def _extract_field(text: str) -> str | None:
        field_keywords = [
            "Computer Science", "Engineering", "Business Administration",
            "Information Technology", "Data Science", "Mathematics",
            "Physics", "Chemistry", "Biology", "Commerce",
            "Arts", "Economics", "Finance", "Marketing",
            "Psychology", "Communications", "Design",
        ]
        lower = text.lower()
        for field in field_keywords:
            if field.lower() in lower:
                return field
        return None


class CertificationMapper:
    """Maps legacy ``CertificationExtractor`` output, adds normalized dates."""

    @staticmethod
    def extract(section_text: str) -> list[CertificationEntry]:
        legacy = CertificationExtractor.extract(section_text)
        entries: list[CertificationEntry] = []
        seen: set[str] = set()
        for item in legacy:
            name = str(item.get("name") or "").strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            dv = parse_single_date(name)
            entries.append(
                CertificationEntry(
                    name=name[:200],
                    issuer=item.get("issuer"),
                    date=dv.original if dv else None,
                    date_iso=dv.iso if dv else None,
                    source_section="certifications",
                )
            )
        return entries


class LanguageMapper:
    @staticmethod
    def extract(section_text: str) -> list[LanguageEntry]:
        return [
            LanguageEntry(language=item["language"], proficiency=item.get("proficiency"))
            for item in LanguageExtractor.extract(section_text)
        ]


class SummaryExtractor:
    """Professional-summary paragraph from summary/objective sections."""

    @staticmethod
    def extract(summary_text: str | None, objective_text: str | None = None) -> str | None:
        for candidate in (summary_text, objective_text):
            if not candidate or not candidate.strip():
                continue
            cleaned: list[str] = []
            for line in candidate.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                if _is_bullet(line):
                    line = _strip_bullet(line)
                cleaned.append(line)
            text = " ".join(cleaned).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) >= 40:
                return text[:600]
        return None
