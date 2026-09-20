"""Candidate Evidence Intelligence engine (Phase 3).

Pure, deterministic computation over the Phase 1 resume profile:

    ResumeProfile + raw text
        ↓
    CandidateEvidenceIndex (reused from Phase 2)
        ↓
    ProfileSnapshot · TimelineInfo · SkillAssessment[] · StrengthInsight[]
        + AchievementInsight[] · ReviewFlag[] · EvidenceGapInsight[]
        + ScreeningQuestionSuggestion[]
        ↓
    Grounded summary (optionally LLM-polished by the service layer)

Grounding and safety rules enforced here:
- NO EVIDENCE = NO CLAIM. A skill listed without support is reported as
  "no detailed supporting evidence", never as "candidate lacks X".
- Confidence describes OUR evidence, not a probability about the candidate.
- Review flags are neutral observations with possible legitimate
  explanations. They never imply dishonesty.
- Achievements are always labelled "Candidate-stated".
- No protected-attribute, personality or performance inference of any kind.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.services.candidate.resume_parser.skill_normalizer import normalize_display
from app.services.candidate.resume_parser.schemas import (
    ExperienceEntry,
    ResumeProfile,
)
from app.services.screening.fit_engine import (
    CandidateEvidenceIndex,
)

ENGINE_VERSION = "intel-1.0.2"  # 1.0.2: legacy self-heal, cert-only entries never become gaps/questions

# Depth ranking (higher is stronger) used to order strengths.
_DEPTH_RANK = {
    "expert_level_evidence": 5,
    "strong": 4,
    "moderate": 3,
    "limited": 2,
    "mention_only": 1,
    "no_evidence": 0,
}
_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "insufficient": 0}

_STATED_YEARS_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b(?!\s*(?:old|of\s*age))"
    r"(?:\s*of)?(?:\s*\w+){0,3}?\s*experience",
    re.IGNORECASE,
)
_ANY_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b(?!\s*(?:old|of\s*age))", re.IGNORECASE)

_MAX_SKILLS_ASSESSED = 30
_MAX_STRENGTHS = 6
_MAX_ACHIEVEMENTS = 8
_MAX_FLAGS_PER_TYPE = 3
_MAX_QUESTIONS = 8
_GAP_MONTHS_THRESHOLD = 12
_OVERLAP_DAYS_THRESHOLD = 31


# ─── date helpers ──────────────────────────────────────────────────────

def _parse_iso_months(value: str | None) -> int | None:
    """Parse an ISO date string ("YYYY-MM" / "YYYY") into absolute months."""
    if not value:
        return None
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?", value.strip())
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 1
    if not 1 <= month <= 12 or year < 1950 or year > 2100:
        return None
    return year * 12 + (month - 1)


def _entry_interval(exp: ExperienceEntry) -> tuple[int | None, int | None]:
    start = _parse_iso_months(exp.start_date)
    end = _parse_iso_months(exp.end_date)
    now_months = datetime.now(timezone.utc).year * 12 + datetime.now(timezone.utc).month - 1
    if exp.is_current:
        end = now_months
    return start, end


def _union_months(intervals: list[tuple[int, int]]) -> int:
    """Total months across merged (non-overlapping) intervals."""
    if not intervals:
        return 0
    ordered = sorted(intervals)
    total = 0
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= cur_end:  # overlap or adjacency → merge
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start + 1
            cur_start, cur_end = start, end
    total += cur_end - cur_start + 1
    return total


def extract_stated_years(summary: str | None, raw_text: str | None) -> float | None:
    """Extract a self-stated years-of-experience figure, if any.

    Returns the highest plausible number explicitly stated near
    "experience"; returns ``None`` when nothing is stated.
    """
    values: list[float] = []
    for text in [summary, raw_text]:
        if not text:
            continue
        for match in _STATED_YEARS_RE.finditer(text):
            try:
                n = float(match.group(1))
            except ValueError:
                continue
            if 0 < n <= 60:
                values.append(n)
    if values:
        return max(values)
    # Fallback: bare "<n>+ years" phrasing in the summary only (too noisy
    # elsewhere — e.g. "5 years managing X" would be a per-role claim).
    if summary:
        for match in _ANY_YEARS_RE.finditer(summary):
            try:
                n = float(match.group(1))
            except ValueError:
                continue
            if 0 < n <= 60:
                values.append(n)
    return max(values) if values else None


# ─── engine ────────────────────────────────────────────────────────────

class CandidateIntelEngine:
    """Computes the full evidence-intelligence result for one candidate."""

    def __init__(self, profile: ResumeProfile | None, raw_text: str | None) -> None:
        self.profile = profile
        self.index = CandidateEvidenceIndex(profile, raw_text)
        self.summary_text = (profile.summary if profile else None) or ""
        self.raw_text = self.index.raw_text

    # ── public entry point ─────────────────────────────────────────────

    def analyze(self) -> dict[str, Any]:
        snapshot = self._snapshot()
        timeline, timeline_flags = self._timeline()
        assessments = self._skill_assessments()
        strengths = self._strengths(assessments)
        achievements = self._achievements()
        gaps = self._evidence_gaps(assessments)
        flags = timeline_flags + self._extra_flags(timeline)
        questions = self._questions(assessments, achievements, flags)
        summary = self._summary(snapshot, strengths, flags, gaps)

        return {
            "snapshot": snapshot,
            "timeline": timeline,
            "strengths": strengths,
            "skill_assessments": assessments[:_MAX_SKILLS_ASSESSED],
            "achievements": achievements,
            "review_flags": flags,
            "evidence_gaps": gaps,
            "screening_questions": questions,
            "summary": summary,
        }

    # ── snapshot ───────────────────────────────────────────────────────

    def _snapshot(self) -> dict[str, Any]:
        profile = self.profile
        exps = list(profile.experience) if profile else []
        intervals = [
            iv for exp in exps
            if (iv := self._dated_interval(exp)) is not None
        ]
        total_months = _union_months(intervals)
        degrees = [
            e.degree for e in (profile.education if profile else []) if e.degree
        ]
        skills_mentioned = len(profile.skills) if profile else 0
        if not profile and self.raw_text:
            # Legacy rows without structured data: dictionary-known words in
            # the candidate's own text are still honest "mentions".
            from app.services.candidate.resume_parser.skill_normalizer import (
                SkillNormalizer,
            )

            skills_mentioned = min(
                len(SkillNormalizer.extract_from_text(self.raw_text)),
                _MAX_SKILLS_ASSESSED,
            )
        return {
            "total_experience_months": total_months,
            "total_experience_years": round(total_months / 12, 1) if total_months else None,
            "experience_count": len(exps),
            "project_count": len(profile.projects) if profile else 0,
            "certification_count": len(profile.certifications) if profile else 0,
            "education_count": len(profile.education) if profile else 0,
            "skills_mentioned": skills_mentioned,
            "highest_degree": degrees[-1] if degrees else None,
        }

    @staticmethod
    def _dated_interval(exp: ExperienceEntry) -> tuple[int, int] | None:
        start, end = _entry_interval(exp)
        if start is None:
            return None
        return start, end if end is not None else start

    # ── timeline consistency ───────────────────────────────────────────

    def _timeline(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        exps = list(self.profile.experience) if self.profile else []
        dated_intervals: list[tuple[int, int]] = []
        entries_with_dates = 0
        for exp in exps:
            iv = self._dated_interval(exp)
            if iv:
                dated_intervals.append(iv)
                entries_with_dates += 1
        computed = _union_months(dated_intervals)
        stated = extract_stated_years(self.summary_text or None, self.raw_text or None)

        info = {
            "computed_months": computed,
            "stated_years_found": stated is not None,
            "stated_years_value": stated,
            "entries_with_dates": entries_with_dates,
            "entries_total": len(exps),
        }
        flags: list[dict[str, Any]] = []

        # 1. Stated experience vs computed timeline.
        if stated is not None and len(exps) > 0:
            computed_years = computed / 12
            delta_years = abs(stated - computed_years)
            if delta_years >= 2.0:
                higher, lower = ("stated", "timeline") if stated > computed_years else ("timeline", "stated")
                flags.append({
                    "flag_type": "stated_vs_timeline_mismatch",
                    "severity": "info",
                    "title": "Stated experience differs from listed roles",
                    "description": (
                        f"The candidate's summary mentions about {stated:g} year(s) of "
                        f"experience, while the dated roles in the resume add up to roughly "
                        f"{computed_years:.1f} year(s). The {higher} figure is higher than the {lower}."
                    ),
                    "possible_explanation": (
                        "The summary may include earlier work, internships, freelance projects or "
                        "roles that are not itemized in the resume's experience section."
                    ),
                    "evidence": [],
                })

        # 2. Overlapping employment periods.
        overlaps = 0
        for i in range(len(exps)):
            for j in range(i + 1, len(exps)):
                a_s, a_e = _entry_interval(exps[i])
                b_s, b_e = _entry_interval(exps[j])
                if None in (a_s, a_e, b_s, b_e):
                    continue
                overlap_days = (min(a_e, b_e) - max(a_s, b_s) + 1) * 30.44
                if overlap_days <= _OVERLAP_DAYS_THRESHOLD:
                    continue
                if overlaps >= _MAX_FLAGS_PER_TYPE:
                    break
                overlaps += 1
                flags.append({
                    "flag_type": "overlapping_employment",
                    "severity": "info",
                    "title": "Overlapping employment dates",
                    "description": (
                        f"The date ranges of '{self.index.experiences[i]['label']}' and "
                        f"'{self.index.experiences[j]['label']}' overlap."
                    ),
                    "possible_explanation": (
                        "Concurrent part-time roles, consulting engagements, contract work or a "
                        "company acquisition are common legitimate reasons for overlapping dates."
                    ),
                    "evidence": [
                        {
                            "source": "experience",
                            "quote": f"{exps[i].original_start_date or exps[i].start_date} – "
                                     f"{exps[i].original_end_date or exps[i].end_date or 'present'}"
                                     f" at {exps[i].company or 'unspecified company'}",
                            "context": self.index.experiences[i]["label"],
                            "section": "Experience",
                        },
                        {
                            "source": "experience",
                            "quote": f"{exps[j].original_start_date or exps[j].start_date} – "
                                     f"{exps[j].original_end_date or exps[j].end_date or 'present'}"
                                     f" at {exps[j].company or 'unspecified company'}",
                            "context": self.index.experiences[j]["label"],
                            "section": "Experience",
                        },
                    ],
                })

        # 3. Internally inconsistent dates (end before start, future start).
        now_ym = datetime.now(timezone.utc).year * 12 + datetime.now(timezone.utc).month - 1
        for exp in exps:
            s, e = _entry_interval(exp)
            if s is None:
                continue
            if e is not None and e < s:
                flags.append({
                    "flag_type": "date_inconsistency",
                    "severity": "warning",
                    "title": "Dates appear inconsistent",
                    "description": (
                        f"The role '{self._exp_display(exp)}' lists an end date earlier than "
                        f"its start date ({exp.start_date} → {exp.end_date})."
                    ),
                    "possible_explanation": "This may simply be a formatting or data-extraction issue.",
                    "evidence": [{
                        "source": "experience",
                        "quote": f"Start: {exp.original_start_date or exp.start_date}; "
                                 f"End: {exp.original_end_date or exp.end_date}",
                        "context": self._exp_display(exp),
                        "section": "Experience",
                    }],
                })
            elif e is None and not exp.is_current and s > now_ym:
                flags.append({
                    "flag_type": "date_inconsistency",
                    "severity": "warning",
                    "title": "Future start date",
                    "description": (
                        f"The role '{self._exp_display(exp)}' appears to start in the future "
                        f"({exp.start_date}) and has no end date."
                    ),
                    "possible_explanation": (
                        "This may be a signed offer starting later, or another extraction artifact."
                    ),
                    "evidence": [{
                        "source": "experience",
                        "quote": f"Start: {exp.original_start_date or exp.start_date}",
                        "context": self._exp_display(exp),
                        "section": "Experience",
                    }],
                })

        return info, flags

    def _extra_flags(self, timeline: dict[str, Any]) -> list[dict[str, Any]]:
        exps = list(self.profile.experience) if self.profile else []
        flags: list[dict[str, Any]] = []
        if exps and timeline["entries_with_dates"] == 0:
            flags.append({
                "flag_type": "missing_dates",
                "severity": "info",
                "title": "Roles have no parseable dates",
                "description": (
                    "None of the listed professional experiences include machine-readable dates, "
                    "so total experience could not be verified from the timeline."
                ),
                "possible_explanation": "Dates may exist but use a format that could not be parsed.",
                "evidence": [],
            })

        # Employment gaps between consecutive dated roles (> threshold months).
        dated = sorted(
            iv for exp in exps
            if not exp.is_current and (iv := self._dated_interval(exp)) is not None
        )
        gaps_found = 0
        for (a_s, a_e), (b_s, _) in zip(dated, dated[1:]):
            gap = b_s - a_e - 1
            if gap < _GAP_MONTHS_THRESHOLD or gaps_found >= 2:
                continue
            gaps_found += 1
            flags.append({
                "flag_type": "employment_gap",
                "severity": "info",
                "title": "Gap in employment timeline",
                "description": (
                    f"There is an unlisted period of about {gap} month(s) between two dated roles."
                ),
                "possible_explanation": (
                    "Career breaks for education, caregiving, health, travel or job search are "
                    "common and neutral; worth a clarifying conversation if relevant to the role."
                ),
                "evidence": [],
            })
        return flags

    @staticmethod
    def _exp_display(exp: ExperienceEntry) -> str:
        parts = [p for p in [exp.job_title or exp.title, exp.company] if p]
        return " — ".join(parts) if parts else "Professional experience"

    # ── skill depth & confidence ───────────────────────────────────────

    def _skill_universe(self) -> list[str]:
        """All distinct skills we can assess, most-mentioned first."""
        freq: dict[str, int] = {}
        display: dict[str, str] = {}
        profile = self.profile
        names: list[str] = []
        if profile:
            names += [s.name for s in profile.skills if s.name]
            for exp in profile.experience:
                names += [t for t in (exp.technologies or []) if t]
            for proj in profile.projects:
                names += [t for t in (proj.technologies or []) if t]
            for cert in profile.certifications:
                if cert.name:
                    names.append(cert.name)
        for name in names:
            key = name.strip()
            if len(key) < 2 or len(key) > 40:
                continue
            low = key.lower()
            freq.setdefault(low, 0)
            freq[low] += 1
            display.setdefault(low, key)
            normalized = normalize_display(low)
            if normalized.lower() == low:
                display[low] = normalized
        ordered = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        names_out = [display[name] for name, _ in ordered[:_MAX_SKILLS_ASSESSED]]

        # Skills that appear ONLY in free text still deserve an honest
        # "insufficient evidence" assessment instead of being invisible.
        if self.raw_text and len(names_out) < _MAX_SKILLS_ASSESSED:
            from app.services.candidate.resume_parser.skill_normalizer import (
                SkillNormalizer,
            )

            known = {n.lower() for n in names_out}
            for found in SkillNormalizer.extract_from_text(self.raw_text):
                if found.name.lower() in known:
                    continue
                known.add(found.name.lower())
                names_out.append(found.name)
                if len(names_out) >= _MAX_SKILLS_ASSESSED:
                    break
        return names_out

    def _assess_skill(self, skill: str) -> dict[str, Any]:
        idx = self.index
        exp_items = idx.find_in_experiences(skill)
        proj_items = idx.find_in_projects(skill)
        cert_items = idx.find_in_certifications(skill)
        edu_items = idx.find_in_education(skill)
        skill_section_items = idx.find_in_skills_section(skill)
        evidence: list[dict[str, Any]] = (
            exp_items[:2] + proj_items[:1] + cert_items[:1]
        )

        matched_labels = {item["context"] for item in exp_items}
        prof_months = sum(
            months for exp in (self.profile.experience if self.profile else [])
            for months in [self._exp_months(exp)]
            if self._exp_label(exp) in matched_labels and months
        )

        counts = {
            "professional_roles": len(exp_items),
            "projects": len(proj_items),
            "certifications": len(cert_items),
            "education": len(edu_items),
            "skills_section": len(skill_section_items),
        }

        depth, confidence, reason = self._classify_depth(
            skill, prof_months, counts,
            bool(evidence or skill_section_items),
        )
        if not evidence:
            raw_items = idx.find_in_raw_text(skill)
            evidence = raw_items[:1]

        return {
            "skill": skill,
            "category": self._skill_category(skill),
            "depth": depth,
            "confidence": confidence,
            "professional_months": prof_months,
            "counts": counts,
            "reason": reason,
            "evidence": evidence[:3],
        }

    def _exp_months(self, exp: ExperienceEntry) -> int:
        if isinstance(exp.duration_months, int) and exp.duration_months > 0:
            return exp.duration_months
        s, e = _entry_interval(exp)
        if s is None:
            return 0
        return max(1, (e if e is not None else s) - s + 1)

    @staticmethod
    def _exp_label(exp: ExperienceEntry) -> str:
        parts = [p for p in [exp.job_title or exp.title, exp.company] if p]
        return " — ".join(parts) if parts else "Professional experience"

    @staticmethod
    def _classify_depth(
        skill: str,
        prof_months: int,
        counts: dict[str, int],
        has_structured_evidence: bool,
    ) -> tuple[str, str, str]:
        """Deterministic depth tier + confidence tier + factual reason.

        The reason NEVER claims the candidate lacks anything; it reports what
        evidence was found (or not found).
        """
        roles = counts["professional_roles"]
        projects = counts["projects"]
        certs = counts["certifications"]
        edu = counts["education"]
        listing = counts["skills_section"]

        # Depth tier.
        if prof_months >= 36 and roles >= 2:
            depth = "expert_level_evidence"
        elif prof_months >= 12 or (prof_months >= 6 and projects >= 1):
            depth = "strong"
        elif prof_months >= 3 or projects >= 2:
            depth = "moderate"
        elif roles >= 1 or projects == 1 or certs >= 1 or edu >= 1:
            depth = "limited"
        elif listing >= 1:
            depth = "mention_only"
        else:
            depth = "mention_only"

        # Confidence in OUR evidence.
        if roles >= 2 or (roles >= 1 and projects >= 1):
            confidence = "high"
        elif roles == 1 or projects >= 2:
            confidence = "medium"
        elif has_structured_evidence:
            confidence = "low"
        else:
            confidence = "insufficient"

        parts: list[str] = []
        if prof_months:
            parts.append(f"about {prof_months // 12}y {prof_months % 12}m of professional use")
        if roles:
            parts.append(f"{roles} role(s)")
        if projects:
            parts.append(f"{projects} project(s)")
        if certs:
            parts.append(f"{certs} certification(s)")
        if edu:
            parts.append("relevant education entry")
        if listing:
            parts.append("skills-section listing")

        if parts:
            reason = f"Evidence found for {skill}: " + ", ".join(parts) + "."
        else:
            reason = (
                f"No structured evidence found for {skill}; it appears only as a plain "
                "text mention in the resume."
            )
        return depth, confidence, reason

    @staticmethod
    def _skill_category(skill: str) -> str | None:
        from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer

        normalized = SkillNormalizer.normalize(skill)
        return normalized.category if normalized else None

    def _skill_assessments(self) -> list[dict[str, Any]]:
        assessments = [self._assess_skill(skill) for skill in self._skill_universe()]
        assessments.sort(key=lambda a: (
            -_DEPTH_RANK[a["depth"]],
            -_CONFIDENCE_RANK[a["confidence"]],
            -a["professional_months"],
            a["skill"],
        ))
        return assessments

    # ── strengths ──────────────────────────────────────────────────────

    def _strengths(self, assessments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        eligible = [
            a for a in assessments
            if _DEPTH_RANK[a["depth"]] >= 3  # moderate and above
        ]
        strengths = []
        for a in eligible[:_MAX_STRENGTHS]:
            strengths.append({
                "title": a["skill"],
                "category": a["category"],
                "depth": a["depth"],
                "confidence": a["confidence"],
                "reason": a["reason"],
                "evidence": a["evidence"],
            })
        return strengths

    # ── achievements ───────────────────────────────────────────────────

    def _achievements(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if not self.profile:
            return items
        for exp in self.profile.experience:
            for text in exp.achievements or []:
                if text and text.strip():
                    items.append({
                        "text": text.strip()[:300],
                        "context": self._exp_label(exp),
                        "source_type": "experience",
                        "label": "Candidate-stated",
                    })
        for proj in self.profile.projects:
            for text in proj.achievements or []:
                if text and text.strip():
                    items.append({
                        "text": text.strip()[:300],
                        "context": proj.name or "Project",
                        "source_type": "project",
                        "label": "Candidate-stated",
                    })
        # Prefer measurable-sounding achievements first, keep stable order otherwise.
        items.sort(key=lambda it: (0 if re.search(r"\d", it["text"]) else 1))
        return items[:_MAX_ACHIEVEMENTS]

    # ── evidence gaps ──────────────────────────────────────────────────

    def _cert_only(self, counts: dict[str, int]) -> bool:
        """True when the only structured evidence is a certification match.

        A certification IS evidence — such entries must not appear as
        "gaps" or drive 'have you worked with X?' questions.
        """
        return (
            counts.get("certifications", 0) > 0
            and counts.get("professional_roles", 0) == 0
            and counts.get("projects", 0) == 0
            and counts.get("education", 0) == 0
            and counts.get("skills_section", 0) == 0
        )

    def _is_certification_name(self, skill: str) -> bool:
        """True when ``skill`` is (part of) a known certification name.

        Legacy parsers often copy certification strings into the skills
        section, so a plain count-based check is not enough here.
        """
        if not self.profile:
            return False
        low = skill.lower()
        for cert in self.profile.certifications:
            name = (cert.name or "").strip().lower()
            if not name:
                continue
            if low == name or low in name or name in low:
                return True
        return False

    def _questionable_gap_entry(self, assessment: dict[str, Any]) -> bool:
        """Should this assessment drive gaps / 'worked with X?' questions?"""
        return (
            self._cert_only(assessment["counts"])
            or self._is_certification_name(assessment["skill"])
        )

    def _evidence_gaps(
        self, assessments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        gaps = []
        for a in assessments:
            if a["depth"] == "mention_only" and a["confidence"] in ("low", "insufficient"):
                if self._questionable_gap_entry(a):
                    continue
                gaps.append({
                    "skill": a["skill"],
                    "current_depth": a["depth"],
                    "note": (
                        f"{a['skill']} is mentioned in the resume without detailed supporting "
                        "evidence. No claim is made either way — consider exploring it in an interview."
                    ),
                })
            if len(gaps) >= 8:
                break
        return gaps

    # ── screening questions ────────────────────────────────────────────

    def _questions(
        self,
        assessments: list[dict[str, Any]],
        achievements: list[dict[str, Any]],
        flags: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        questions: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(question: str, topic: str, reason: str) -> None:
            if question.lower() in seen or len(questions) >= _MAX_QUESTIONS:
                return
            seen.add(question.lower())
            questions.append({"question": question, "topic": topic, "reason": reason})

        thin = [
            a for a in assessments
            if a["depth"] in ("mention_only", "limited")
            and not self._questionable_gap_entry(a)
        ][:3]
        for a in thin:
            add(
                f"Can you describe a specific situation where you worked with {a['skill']}?",
                "skill evidence",
                f"The resume lists {a['skill']} without detailed supporting evidence.",
            )

        quantified = [ach for ach in achievements if re.search(r"\d", ach["text"])][:2]
        for ach in quantified:
            add(
                f"Could you walk us through how you achieved: \"{ach['text']}\"?",
                "achievement verification",
                "Achievement stated by the candidate on their resume; details have not been independently verified.",
            )

        for flag in flags:
            if flag["flag_type"] == "overlapping_employment":
                add(
                    "We noticed some of the listed roles have overlapping dates. "
                    "Could you clarify whether these were concurrent or part-time engagements?",
                    "timeline clarification",
                    flag["description"] + " Overlapping dates can have many legitimate explanations.",
                )
            elif flag["flag_type"] == "stated_vs_timeline_mismatch":
                add(
                    "Your resume summary mentions more experience than the individual roles "
                    "add up to. Could you help us understand what the additional time included?",
                    "experience reconciliation",
                    flag["description"],
                )

        strong = [a for a in assessments if a["depth"] in ("expert_level_evidence", "strong")]
        if strong and len(questions) < 3:
            top = strong[0]["skill"]
            add(
                f"In which project did you apply {top} most deeply, and what was your specific contribution?",
                "depth exploration",
                f"{top} shows the strongest evidence in this resume; deeper detail helps calibrate level.",
            )
        return questions

    # ── grounded deterministic summary ─────────────────────────────────

    def _summary(
        self,
        snapshot: dict[str, Any],
        strengths: list[dict[str, Any]],
        flags: list[dict[str, Any]],
        gaps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        years = snapshot.get("total_experience_years")
        name_bits: list[str] = []
        if snapshot.get("experience_count"):
            name_bits.append(f"{snapshot['experience_count']} listed role(s)")
        if snapshot.get("project_count"):
            name_bits.append(f"{snapshot['project_count']} project(s)")
        if snapshot.get("certification_count"):
            name_bits.append(f"{snapshot['certification_count']} certification(s)")

        exp_phrase = (
            f"About {years:g} years of professional experience"
            if years else "Professional experience could not be determined from the resume"
        )
        strength_names = ", ".join(s["title"] for s in strengths[:3]) if strengths else None
        sentences = [f"{exp_phrase}" + (f" across {' and '.join(name_bits)}." if name_bits else ".")]
        if strength_names:
            strongest = strengths[0]
            sentences.append(
                f"Strongest documented areas: {strength_names} ({strongest['depth'].replace('_', ' ')})"
            )
        else:
            sentences.append(
                "No strongly evidenced core skills were identified from the resume alone; "
                "this reflects available evidence, not a judgment of the candidate."
            )
        if flags:
            sentences.append(f"{len(flags)} timeline observation(s) flagged for optional human review.")
        if gaps:
            sentences.append(
                f"{len(gaps)} skill mention(s) lack detailed supporting evidence; "
                "these may be worth exploring in conversation."
            )
        text = " ".join(sentences)
        return {
            "text": text,
            "source": "deterministic",
            "disclaimer": (
                "AI-assisted evidence analysis based on resume content. "
                "This is decision support, not a hiring decision."
            ),
        }


# ─── job-contextual composition (over the Phase 2 fit result) ─────────

def build_job_context(fit_result: dict[str, Any]) -> dict[str, Any]:
    """Compose job-specific intelligence from a cached/generated fit result.

    Reuses the Phase 2 fit analysis rather than recomputing matching logic.
    """
    requirements = fit_result.get("requirements") or []
    gaps = [r["requirement"] for r in requirements if r.get("status") == "gap"]
    unknown = [r["requirement"] for r in requirements if r.get("status") == "unknown"]

    alignment = fit_result.get("experience_alignment") or {}
    questions = []
    for req in (unknown + gaps)[:3]:
        questions.append({
            "question": (
                f"The resume does not provide clear evidence for \"{req}\". "
                "Could you describe your experience with it?"
            ),
            "topic": "job requirement",
            "reason": (
                "Listed as a job requirement, but no clear supporting evidence "
                "was found in this resume."
            ),
        })

    overall = fit_result.get("overall") or {}
    classification = overall.get("classification", "unknown")
    score = overall.get("score", 0)
    parts: list[str] = [
        f"For {fit_result.get('job_title', 'this role')} the evidence-based assessment is "
        f"\"{classification.replace('_', ' ')}\" (score {score}/100, transparent weighting shown above)."
    ]
    if alignment.get("required_years"):
        basis = alignment.get("relevance_basis")
        years_val = alignment.get("relevant_years") if basis == "relevant_experience" else alignment.get("total_years")
        label = "relevant" if basis == "relevant_experience" else "total"
        years_text = f"~{years_val:g} year(s)" if isinstance(years_val, (int, float)) else "an undetermined amount"
        parts.append(
            f"The role asks for ~{alignment['required_years']:g} year(s); "
            f"the resume evidences {years_text} of {label} experience."
        )
    if unknown:
        parts.append(f"{len(unknown)} requirement(s) could not be assessed from the resume.")
    text = " ".join(parts)

    return {
        "job_id": fit_result.get("job_id"),
        "job_title": fit_result.get("job_title"),
        "fit_classification": classification,
        "fit_score": int(score or 0),
        "required_years": alignment.get("required_years"),
        "relevant_years": alignment.get("relevant_years"),
        "total_years": alignment.get("total_years"),
        "relevance_basis": alignment.get("relevance_basis"),
        "requirement_gaps": gaps,
        "requirement_unknown": unknown,
        "additional_questions": questions,
        "summary": {
            "text": text,
            "source": "deterministic",
            "disclaimer": (
                "AI-assisted evidence analysis based on resume content. "
                "This is decision support, not a hiring decision."
            ),
        },
    }


def run_intel_analysis(profile_json: dict[str, Any] | None, raw_text: str | None) -> dict[str, Any]:
    """Convenience wrapper mirroring ``run_fit_analysis``."""
    profile = build_profile_from_dict(profile_json)
    return CandidateIntelEngine(profile, raw_text).analyze()


def build_profile_from_dict(data: dict[str, Any] | None) -> ResumeProfile | None:
    """Safely hydrate a Phase 1 ResumeProfile from stored JSON.

    Legacy payloads missing the (later-added) ``metadata`` block are
    completed with defaults instead of being dropped entirely.
    """
    if not isinstance(data, dict) or not data:
        return None
    try:
        return ResumeProfile.model_validate(data)
    except Exception:  # noqa: BLE001
        try:
            patched = {**data}
            patched.setdefault("metadata", {
                "parser_version": "legacy",
                "processed_at": "1970-01-01T00:00:00Z",
            })
            return ResumeProfile.model_validate(patched)
        except Exception:  # noqa: BLE001 — malformed payloads degrade gracefully
            return None
