"""Evidence-grounded fit engine (Phase 2).

Pure, deterministic computation:

    JobRequirements (from requirement_extractor)
        +
    CandidateEvidenceIndex (from Phase 1 ResumeProfile + raw text)
        ↓
    RequirementResult[]   (MATCH / PARTIAL / GAP / UNKNOWN + evidence)
        ↓
    ExperienceAlignment · ResponsibilityAlignment[] · SkillGapSummary
        ↓
    OverallFit (transparent weighted score + grounded summary)

Grounding rules enforced here:
- NO EVIDENCE = NO CLAIM. Absence of evidence is reported as "no supporting
  evidence found", never as "candidate lacks X".
- UNKNOWN explicitly means "the resume does not provide enough evidence".
- Every evidence item quotes actual resume content.
"""

from __future__ import annotations

import math
import re
from typing import Any

from app.services.candidate.resume_parser.schemas import (
    ExperienceEntry,
    ResumeProfile,
)
from app.services.screening.matching_engine import MatchingEngine
from app.services.screening.skill_graph import SkillGraph

ENGINE_VERSION = "fit-1.1.0"  # 1.1.0: raw-text evidence layer + strict LLM polish contract

# ─── Transparent scoring configuration (visible, documented) ─────────────
# Overall score = Σ weight_i × credit_i over available components.
# Components with no data (None) are excluded and their weight is
# redistributed proportionally across the remaining components.
FIT_WEIGHTS: dict[str, float] = {
    "required_skills": 0.45,
    "experience": 0.25,
    "responsibilities": 0.15,
    "preferred_skills": 0.15,
}
# Per-requirement credit used inside each component (0.0 – 1.0).
# UNKNOWN earns neutral credit: unresolved requirements neither reward nor
# penalize the candidate, they reduce confidence (see insufficient-evidence
# override below).
STATUS_CREDIT: dict[str, float] = {
    "match": 1.0,
    "partial": 0.5,
    "gap": 0.0,
    "unknown": 0.5,
}
RESPONSIBILITY_CREDIT: dict[str, float] = {
    "strong": 1.0,
    "moderate": 0.7,
    "weak": 0.4,
    "none": 0.1,
}

CLASSIFICATION_THRESHOLDS: list[tuple[float, str]] = [
    (80.0, "strong_match"),
    (65.0, "good_match"),
    (45.0, "partial_match"),
]

# Literal text variants used when searching resume prose for a skill.
_EXTRA_TOKEN_VARIANTS: dict[str, list[str]] = {
    "kubernetes": ["k8s"],
    "javascript": ["js"],
    "typescript": ["ts"],
    "postgresql": ["postgres"],
    "mongodb": ["mongo"],
    "machine learning": ["ml"],
    "natural language processing": ["nlp"],
    "generative ai": ["genai", "gen ai"],
    "continuous integration": ["ci"],
}
_STOPWORDS = {
    "the", "and", "for", "with", "using", "our", "you", "will", "are", "have",
    "has", "this", "that", "all", "new", "who", "can", "their", "your", "from",
    "across", "into", "about", "team", "work", "role", "help", "join",
}


def _token_variants(name: str) -> list[str]:
    lower = name.lower()
    variants = [re.escape(lower)]
    variants.extend(re.escape(v) for v in _EXTRA_TOKEN_VARIANTS.get(lower, []))
    synonyms = SkillGraph.SYNONYMS.get(lower, [])
    variants.extend(re.escape(s.lower()) for s in synonyms if s.lower() != lower)
    return variants


def _token_pattern(name: str) -> re.Pattern[str]:
    joined = "|".join(sorted(set(_token_variants(name)), key=len, reverse=True))
    return re.compile(r"(?<![a-z0-9+#])(" + joined + r")(?![a-z0-9+#])", re.IGNORECASE)


def _sentences_of(texts: list[str]) -> list[str]:
    out: list[str] = []
    for text in texts:
        for part in re.split(r"(?<=[.;!?])\s+|\n+", text or ""):
            part = part.strip()
            if len(part) >= 8:
                out.append(part)
    return out


class CandidateEvidenceIndex:
    """Searchable index over the structured Phase 1 resume profile."""

    def __init__(self, profile: ResumeProfile | None, raw_text: str | None) -> None:
        self.profile = profile
        self.raw_text = (raw_text or "").strip()
        self.raw_sentences: list[str] = _sentences_of([self.raw_text]) if self.raw_text else []
        self.experiences: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.certifications: list[dict[str, Any]] = []
        self.education: list[dict[str, Any]] = []
        self.skills_only: list[dict[str, Any]] = []

        if profile:
            for exp in profile.experience:
                self.experiences.append({
                    "entry": exp,
                    "label": self._exp_label(exp),
                    "tech": [t for t in exp.technologies or []],
                    "sentences": _sentences_of(
                        (exp.description or []) + (exp.responsibilities or [])
                        + (exp.achievements or [])
                    ),
                })
            for proj in profile.projects:
                self.projects.append({
                    "entry": proj,
                    "label": proj.name or "Project",
                    "tech": [t for t in proj.technologies or []],
                    "sentences": _sentences_of(
                        (proj.description or []) + (proj.responsibilities or [])
                        + (proj.achievements or [])
                    ),
                })
            for cert in profile.certifications:
                self.certifications.append({
                    "name": cert.name,
                    "issuer": cert.issuer,
                    "quote": cert.name,
                })
            for edu in profile.education:
                fields = [edu.degree or "", edu.field_of_study or ""]
                self.education.append({
                    "degree": edu.degree,
                    "field": edu.field_of_study,
                    "text": " ".join(f for f in fields if f).strip(),
                })
            for skill in profile.skills:
                self.skills_only.append(skill.model_dump(mode="json"))

    @staticmethod
    def _exp_label(exp: ExperienceEntry) -> str:
        parts = [p for p in [exp.job_title or exp.title, exp.company] if p]
        return " — ".join(parts) if parts else "Professional experience"

    def has_any_data(self) -> bool:
        return bool(
            self.experiences or self.projects or self.certifications
            or self.education or self.skills_only or self.raw_text
        )

    # ── search helpers ─────────────────────────────────────────────────

    @staticmethod
    def _matching_sentences(
        sentences: list[str], pattern: re.Pattern[str], limit: int = 2,
    ) -> list[str]:
        hits: list[str] = []
        for sentence in sentences:
            if pattern.search(sentence):
                hits.append(sentence)
                if len(hits) >= limit:
                    break
        return hits

    def find_in_experiences(self, requirement: str) -> list[dict[str, Any]]:
        """Evidence items for ``requirement`` found in professional experience."""
        pattern = _token_pattern(requirement)
        items: list[dict[str, Any]] = []
        for exp in self.experiences:
            tech_hits = [
                t for t in exp["tech"]
                if MatchingEngine.skill_matches(t, requirement)
            ]
            sentence_hits = self._matching_sentences(exp["sentences"], pattern)
            if not tech_hits and not sentence_hits:
                continue
            quote = sentence_hits[0] if sentence_hits else ", ".join(tech_hits)
            items.append({
                "source": "experience",
                "quote": quote[:300],
                "context": exp["label"],
                "section": "Experience",
            })
        return items

    def find_in_projects(self, requirement: str) -> list[dict[str, Any]]:
        pattern = _token_pattern(requirement)
        items: list[dict[str, Any]] = []
        for proj in self.projects:
            tech_hits = [
                t for t in proj["tech"]
                if MatchingEngine.skill_matches(t, requirement)
            ]
            sentence_hits = self._matching_sentences(proj["sentences"], pattern)
            if not tech_hits and not sentence_hits:
                continue
            quote = sentence_hits[0] if sentence_hits else ", ".join(tech_hits)
            items.append({
                "source": "project",
                "quote": quote[:300],
                "context": proj["label"],
                "section": "Projects",
            })
        return items

    def find_in_certifications(self, requirement: str) -> list[dict[str, Any]]:
        return [
            {
                "source": "certification",
                "quote": cert["name"][:300],
                "context": cert["issuer"] or "Certification",
                "section": "Certifications",
            }
            for cert in self.certifications
            if MatchingEngine.skill_matches(cert["name"], requirement)
        ]

    def find_in_education(self, requirement: str) -> list[dict[str, Any]]:
        pattern = _token_pattern(requirement)
        return [
            {
                "source": "education",
                "quote": edu["text"][:300],
                "context": "Education",
                "section": "Education",
            }
            for edu in self.education
            if edu["text"] and pattern.search(edu["text"].lower())
        ]

    def find_in_skills_section(self, requirement: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for skill in self.skills_only:
            name = skill.get("name") or ""
            if MatchingEngine.skill_matches(name, requirement):
                items.append({
                    "source": "skills_section",
                    "quote": name,
                    "context": "Listed under "
                    + (skill.get("source_section") or "Skills"),
                    "section": skill.get("source_section") or "Skills",
                })
        return items

    def find_in_raw_text(self, requirement: str) -> list[dict[str, Any]]:
        """Deterministic scan over the raw resume text.

        Resumes whose structured profile is missing or sparse (e.g. legacy
        parsed data) still contain real evidence — a literal mention in the
        candidate's own text must never be reported as a gap.
        """
        if not self.raw_sentences:
            return []
        pattern = _token_pattern(requirement)
        return [
            {
                "source": "resume_text",
                "quote": sentence[:300],
                "context": "Resume text",
                "section": "Resume",
            }
            for sentence in self._matching_sentences(self.raw_sentences, pattern)
        ]

    def related_known_skills(self, requirement: str) -> list[str]:
        related: list[str] = []
        names = [s.get("name", "") for s in self.skills_only]
        names += [t for exp in self.experiences for t in exp["tech"]]
        for name in names:
            if not name:
                continue
            sim = SkillGraph.similarity_score(name, requirement)
            if 0.55 <= sim < 0.99 and name not in related:
                related.append(name)
        return related[:3]


class FitEngine:
    """Computes the full evidence-grounded fit result."""

    def __init__(
        self,
        job_title: str,
        requirements: dict[str, Any],
        evidence: CandidateEvidenceIndex,
    ) -> None:
        self.job_title = job_title
        self.requirements = requirements
        self.evidence = evidence

    # ─── public entry point ────────────────────────────────────────────

    def analyze(self) -> dict[str, Any]:
        requirement_results = self._analyze_skill_requirements()

        min_years = self.requirements.get("minimum_experience_years")
        experience_alignment = self._align_experience(min_years)

        responsibilities = self._align_responsibilities(
            self.requirements.get("responsibilities") or []
        )

        education_result = self._analyze_education_requirement()
        certification_results = self._analyze_certification_requirements()
        requirement_results = (
            certification_results
            + ([education_result] if education_result else [])
            + requirement_results
        )

        skill_gaps = self._build_skill_gaps(requirement_results)
        overall = self._compute_overall(
            requirement_results, experience_alignment, responsibilities,
        )

        return {
            "requirements": requirement_results,
            "experience_alignment": experience_alignment,
            "responsibilities": responsibilities,
            "skill_gaps": skill_gaps,
            "overall": overall,
        }

    # ─── Feature 3/4/6: evidence mapping + status + strength ───────────

    def _analyze_skill_requirements(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for level in ("required", "preferred"):
            for skill in self.requirements.get(f"{level}_skills") or []:
                name = skill.get("name") or ""
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                results.append(self._map_single_skill(name, skill.get("category"), level))
        return results

    def _map_single_skill(
        self, name: str, category: str | None, level: str,
    ) -> dict[str, Any]:
        evidence: list[dict[str, Any]] = []

        exp_items = self.evidence.find_in_experiences(name)
        proj_items = self.evidence.find_in_projects(name)
        cert_items = self.evidence.find_in_certifications(name)
        edu_items = self.evidence.find_in_education(name)
        skill_items = self.evidence.find_in_skills_section(name)

        evidence.extend(exp_items + proj_items + cert_items + edu_items)

        if exp_items:
            strength = "strong"
            reason = f"Professional experience directly supports {name}."
        elif proj_items or cert_items:
            strength = "moderate"
            source = "project work" if proj_items else "certifications"
            reason = f"{name} is supported by candidate {source}, but not by listed professional experience."
        elif edu_items:
            strength = "weak"
            reason = f"{name} appears only in the candidate's education background."
        elif skill_items:
            strength = "weak"
            reason = f"{name} is listed in the resume skills section without supporting experience details."
        else:
            strength = "none"

        if strength == "none":
            # A literal mention anywhere in the resume text is real evidence
            # (weaker than structured experience, stronger than inference).
            raw_items = self.evidence.find_in_raw_text(name)
            if raw_items:
                return self._result(
                    requirement=name, category=category, level=level,
                    status="partial", strength="moderate",
                    reason=(
                        f"{name} is mentioned in the resume text, but not in a "
                        "structured experience or skills section."
                    ),
                    evidence=raw_items,
                )
            # Related/transferable skill detection before concluding anything.
            related = self.evidence.related_known_skills(name)
            if related:
                return self._result(
                    requirement=name, category=category, level=level,
                    status="partial", strength="weak",
                    reason=(
                        f"No direct evidence for {name}; closest related skill(s) found: "
                        + ", ".join(related) + "."
                    ),
                    evidence=[],
                )
            passage = self._fallback_passage(name)
            if passage:
                evidence.append(passage)
                return self._result(
                    requirement=name, category=category, level=level,
                    status="partial", strength="weak",
                    reason=f"{name} is mentioned in the resume text, but only outside structured sections.",
                    evidence=[passage],
                )
            if self.evidence.has_any_data():
                return self._result(
                    requirement=name, category=category, level=level,
                    status="gap", strength="none",
                    reason=(
                        f"No supporting evidence for {name} was found anywhere in the resume."
                    ),
                    evidence=[],
                )
            return self._result(
                requirement=name, category=category, level=level,
                status="unknown", strength="none",
                reason=(
                    f"The resume does not provide enough information to evaluate {name}."
                ),
                evidence=[],
            )

        status = "match" if strength in ("strong", "moderate") else "partial"
        return self._result(
            requirement=name, category=category, level=level,
            status=status, strength=strength, reason=reason, evidence=evidence,
        )

    def _fallback_passage(self, name: str) -> dict[str, Any] | None:
        """Last-resort retrieval over the raw resume text.

        Uses the existing embedding service (RAG infrastructure) to rank
        passages, then verifies the skill token literally appears in the
        passage before returning it — so the quote is always real text.
        """
        if not self.evidence.raw_text:
            return None
        try:
            from app.rag.embeddings import embedding_service

            pattern = _token_pattern(name)
            chunks = [
                c.strip() for c in re.split(r"\n\s*\n", self.evidence.raw_text)
                if 40 <= len(c.strip()) <= 600
            ]
            if not chunks:
                return None
            query = embedding_service.embed_query(name)
            if not query:
                return None

            def cosine(a: list[float], b: list[float]) -> float:
                dot = sum(x * y for x, y in zip(a, b))
                na = math.sqrt(sum(x * x for x in a)) or 1e-9
                nb = math.sqrt(sum(y * y for y in b)) or 1e-9
                return dot / (na * nb)

            scored = sorted(
                ((cosine(query, embedding_service.embed_query(c)), c) for c in chunks[:120]),
                key=lambda pair: -pair[0],
            )
            for _score, chunk in scored[:5]:
                if pattern.search(chunk.lower()):
                    return {
                        "source": "resume_text",
                        "quote": chunk[:300],
                        "context": "Resume text",
                        "section": "Resume",
                    }
        except Exception:  # noqa: BLE001 — retrieval failure must never break matching
            return None
        return None

    # ─── Feature 8: experience alignment ───────────────────────────────

    def _align_experience(self, min_years: float | None) -> dict[str, Any]:
        base: dict[str, Any] = {
            "status": "unknown",
            "required_years": min_years,
            "relevant_years": None,
            "total_years": None,
            "relevance_basis": "none",
            "reason": "",
        }
        if min_years is None:
            base["reason"] = "No minimum experience requirement was extracted from this job."
            return base

        experiences = self.evidence.experiences
        total_months = 0.0
        relevant_months = 0.0
        durations_known = False
        job_terms = self._job_context_terms()

        for exp in experiences:
            entry: ExperienceEntry = exp["entry"]
            months = entry.duration_months
            if months is None:
                continue
            durations_known = True
            total_months += months
            if self._experience_is_relevant(exp, job_terms):
                relevant_months += months

        total_years = round(total_months / 12, 1) if durations_known else None
        relevant_years = round(relevant_months / 12, 1) if durations_known else None
        base["total_years"] = total_years
        base["relevant_years"] = relevant_years

        if not durations_known:
            base["reason"] = (
                "Resume does not provide reliable employment dates to evaluate "
                "the experience requirement."
            )
            return base

        if relevant_years and relevant_years > 0:
            base["relevance_basis"] = "relevant_experience"
            comparable = relevant_years
        else:
            # Relevance cannot be established from titles/technologies; fall
            # back to total experience and downgrade to PARTIAL.
            base["relevance_basis"] = "total_experience"
            comparable = total_years or 0.0

        if comparable >= min_years:
            if base["relevance_basis"] == "total_experience":
                base["status"] = "partial"
                base["reason"] = (
                    f"Candidate shows {total_years:.1f} total years of experience; "
                    f"relevance to this role could not be reliably established "
                    f"(requirement: {min_years:g}+ years)."
                )
            else:
                base["status"] = "match"
                base["reason"] = (
                    f"Candidate has approximately {relevant_years:.1f} years of "
                    f"relevant experience (requirement: {min_years:g}+ years)."
                )
        else:
            base["status"] = "partial"
            basis = (
                "relevant experience" if base["relevance_basis"] == "relevant_experience"
                else "total experience"
            )
            base["reason"] = (
                f"Candidate shows approximately {comparable:.1f} years of {basis}, "
                f"below the {min_years:g}-year requirement."
            )
        return base

    def _job_context_terms(self) -> set[str]:
        terms: set[str] = set()
        for word in re.findall(r"[a-zA-Z]{3,}", self.job_title or ""):
            lowered = word.lower()
            if lowered not in _STOPWORDS:
                terms.add(lowered)
        for level in ("required", "preferred"):
            for skill in self.requirements.get(f"{level}_skills") or []:
                name = (skill.get("name") or "").lower()
                if name:
                    terms.add(name)
        return terms

    def _experience_is_relevant(self, exp: dict[str, Any], job_terms: set[str]) -> bool:
        entry = exp["entry"]
        title = (entry.job_title or entry.title or "").lower()
        for term in job_terms:
            if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", title):
                return True
        haystack = " ".join([*exp["tech"], *exp["sentences"]]).lower()
        hits = sum(1 for term in job_terms if term in haystack)
        return hits >= max(2, len(job_terms) // 3)

    # ─── Feature 9: responsibility alignment ───────────────────────────

    def _align_responsibilities(
        self, responsibilities: list[str],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        candidate_sentences: list[tuple[str, dict[str, Any] | None, str]] = []
        for exp in self.evidence.experiences:
            label = exp["label"]
            for sentence in exp["sentences"]:
                candidate_sentences.append((sentence.lower(), exp, label))
        for proj in self.evidence.projects:
            label = f"{proj['label']} (Project)"
            for sentence in proj["sentences"]:
                candidate_sentences.append((sentence.lower(), proj, label))

        for responsibility in responsibilities:
            terms = self._content_terms(responsibility)
            best_overlap = 0.0
            best_item: tuple[str, dict[str, Any] | None, str] | None = None
            for lowered, source, label in candidate_sentences:
                overlap = len(terms & self._content_terms(lowered)) / max(len(terms), 1)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_item = (lowered, source, label)
            # Unstructured fallback: scan the raw resume text when no
            # structured section aligns, capping credit at "weak".
            raw_quote: str | None = None
            if best_overlap < 0.25 and self.evidence.raw_sentences:
                for sentence in self.evidence.raw_sentences:
                    lowered = sentence.lower()
                    overlap = len(terms & self._content_terms(lowered)) / max(len(terms), 1)
                    if overlap >= 0.25 and overlap > best_overlap:
                        best_overlap = overlap
                        raw_quote = sentence[:300]
                        break
            if raw_quote is not None:
                results.append({
                    "responsibility": responsibility,
                    "alignment": "weak",
                    "evidence": [{
                        "source": "resume_text",
                        "quote": raw_quote,
                        "context": "Resume text",
                        "section": "Resume",
                    }],
                })
            elif best_item and best_overlap >= 0.25:
                alignment = (
                    "strong" if best_overlap >= 0.45
                    else "moderate" if best_overlap >= 0.35
                    else "weak"
                )
                source_obj = best_item[1]
                is_experience = isinstance(source_obj.get("entry"), ExperienceEntry)
                evidence = [{
                    "source": "experience" if is_experience else "project",
                    "quote": self._original_sentence(best_item),
                    "context": best_item[2],
                    "section": "Experience" if is_experience else "Projects",
                }]
                results.append({
                    "responsibility": responsibility,
                    "alignment": alignment,
                    "evidence": evidence,
                })
            else:
                results.append({
                    "responsibility": responsibility,
                    "alignment": "none",
                    "evidence": [],
                })
        return results

    @staticmethod
    def _original_sentence(item: tuple[str, dict[str, Any], str]) -> str:
        lowered, source, _label = item
        for sentence in source["sentences"]:
            if sentence.lower() == lowered:
                return sentence[:300]
        return lowered[:300]

    @staticmethod
    def _content_terms(text: str) -> set[str]:
        words = re.findall(r"[a-z][a-z0-9+#]{2,}", (text or "").lower())
        return {w for w in words if w not in _STOPWORDS}

    # ─── Education / certification requirements ────────────────────────

    _DEGREE_TOKEN_RE = re.compile(
        r"\b(bachelor(?:'s)?|master(?:'s)?|phd|doctorate|mba|associate(?:'s)?|diploma|"
        r"b\.?(?:tech|sc)|m\.?(?:tech|sc)|b\.?eng\b|m\.?eng\b|"
        r"b\.s\b|m\.s\b|b\.a\b)",
        re.IGNORECASE,
    )

    def _raw_text_education_evidence(self) -> list[dict[str, Any]]:
        for sentence in self.evidence.raw_sentences:
            if self._DEGREE_TOKEN_RE.search(sentence):
                return [{
                    "source": "resume_text",
                    "quote": sentence[:300],
                    "context": "Resume text",
                    "section": "Resume",
                }]
        return []

    def _analyze_education_requirement(self) -> dict[str, Any]:
        text = (self.requirements.get("education") or "").strip()
        if not text:
            return {}
        degrees = [edu["text"] for edu in self.evidence.education if edu["text"]]
        evidence = [
            {
                "source": "education",
                "quote": d[:300],
                "context": "Education",
                "section": "Education",
            }
            for d in degrees
        ]
        if not degrees:
            # Structured education missing — a degree mention in the raw
            # resume text still counts as partial (unstructured) evidence.
            raw_edu = self._raw_text_education_evidence()
            if raw_edu:
                return self._result(
                    requirement=text[:120], category=None, level="required",
                    requirement_type="education",
                    status="partial", strength="weak",
                    reason=(
                        "Education is mentioned only in the resume text, not "
                        "in a structured education section."
                    ),
                    evidence=raw_edu,
                )
            return self._result(
                requirement=text[:120], category=None, level="required",
                requirement_type="education",
                status="unknown" if not self.evidence.has_any_data() else "gap",
                strength="none",
                reason=(
                    "No education information was found in the resume."
                    if self.evidence.has_any_data()
                    else "The resume does not provide enough information to evaluate education."
                ),
                evidence=[],
            )
        score = MatchingEngine.calculate_education_match(degrees, text)
        if score >= 100:
            status, strength, reason = "match", "strong", (
                f"Candidate education meets the requirement ({text[:80]})."
            )
        elif score >= 65:
            status, strength, reason = "partial", "moderate", (
                f"Candidate education is close to but below the stated requirement ({text[:80]})."
            )
        else:
            status, strength, reason = "gap", "none", (
                f"Candidate education appears below the stated requirement ({text[:80]})."
            )
        return self._result(
            requirement=text[:120], category=None, level="required",
            requirement_type="education", status=status, strength=strength,
            reason=reason, evidence=evidence[:2],
        )

    def _analyze_certification_requirements(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for statement in self.requirements.get("certifications") or []:
            cert_names = [c["name"] for c in self.evidence.certifications]
            matched = [
                cn for cn in cert_names
                if MatchingEngine.skill_matches(cn, statement)
            ]
            evidence = [
                {
                    "source": "certification",
                    "quote": m[:300],
                    "context": "Certification",
                    "section": "Certifications",
                }
                for m in matched
            ]
            if matched:
                status, strength, reason = "match", "moderate", (
                    f"Resume lists a matching certification: {matched[0][:80]}."
                )
            else:
                status, strength, reason = "gap", "none", (
                    "No matching certification was found in the resume."
                )
            results.append(self._result(
                requirement=statement[:120], category=None, level="preferred",
                requirement_type="certification", status=status,
                strength=strength, reason=reason, evidence=evidence,
            ))
        return results

    # ─── Feature 7: skill gap summary ──────────────────────────────────

    def _build_skill_gaps(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        gaps = SkillGapBuilder()
        for r in results:
            if r["requirement_type"] != "skill":
                continue
            label = r["requirement"]
            prefix = "" if r["level"] == "required" else " (preferred)"
            if r["status"] == "match":
                gaps.strengths.append(label + prefix)
            elif r["status"] == "partial":
                gaps.partial.append(label + prefix)
            elif r["status"] == "gap":
                gaps.gaps.append(label + prefix)
            else:
                gaps.unknown.append(label + prefix)
        return gaps.to_dict()

    # ─── Feature 10: overall fit (transparent) ─────────────────────────

    def _compute_overall(
        self,
        results: list[dict[str, Any]],
        experience_alignment: dict[str, Any],
        responsibilities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        skill_results = [r for r in results if r["requirement_type"] == "skill"]

        def component_credit(items: list[dict[str, Any]]) -> float | None:
            if not items:
                return None
            return sum(STATUS_CREDIT[r["status"]] for r in items) / len(items)

        required_credit = component_credit(
            [r for r in skill_results if r["level"] == "required"])
        preferred_credit = component_credit(
            [r for r in skill_results if r["level"] == "preferred"])

        experience_credit: float | None = None
        if experience_alignment["required_years"] is not None:
            experience_credit = STATUS_CREDIT[experience_alignment["status"]]

        responsibility_credit: float | None = None
        if responsibilities:
            responsibility_credit = sum(
                RESPONSIBILITY_CREDIT[r["alignment"]] for r in responsibilities
            ) / len(responsibilities)

        components: dict[str, float | None] = {
            "required_skills": required_credit,
            "experience": experience_credit,
            "responsibilities": responsibility_credit,
            "preferred_skills": preferred_credit,
        }
        active = {
            key: FIT_WEIGHTS[key]
            for key, value in components.items()
            if value is not None
        }
        weight_sum = sum(active.values())
        score = int(round(sum(
            components[key] * weight for key, weight in active.items()
        ) / weight_sum * 100)) if weight_sum else 0

        classification = "low_match"
        for threshold, label in CLASSIFICATION_THRESHOLDS:
            if score >= threshold:
                classification = label
                break

        # Insufficient-evidence override: when most requirements could not be
        # evaluated (or there is essentially no resume data), the honest answer
        # is "insufficient evidence", regardless of the numeric score.
        evaluable = [r for r in skill_results if r["status"] != "unknown"]
        coverage = (
            len(evaluable) / len(skill_results) if skill_results else 1.0
        )
        if not self.evidence.has_any_data() or coverage < 0.5:
            classification = "insufficient_evidence"

        summary = self._build_summary(classification, skill_results, experience_alignment)

        return {
            "classification": classification,
            "score": score,
            "breakdown": {
                "weights": FIT_WEIGHTS,
                "components": components,
                "formula": (
                    "score = Σ(weightᵢ × creditᵢ) / Σ(weightᵢ) × 100 over available "
                    "components; credits: match=1.0, partial=0.5, gap=0.0, unknown=0.5 "
                    "(per requirement) and strong=1.0, moderate=0.7, weak=0.4, none=0.1 "
                    "(per responsibility). Components without data are excluded and "
                    "their weight redistributed. Weights: required_skills=0.45, "
                    "experience=0.25, responsibilities=0.15, preferred_skills=0.15."
                ),
            },
            "summary": summary,
            "summary_source": "deterministic",
            "disclaimer": (
                "AI-assisted fit assessment based on resume evidence. "
                "This is decision support, not a hiring decision."
            ),
        }

    def _build_summary(
        self,
        classification: str,
        skill_results: list[dict[str, Any]],
        experience_alignment: dict[str, Any],
    ) -> str:
        opener = {
            "strong_match": f"Strong alignment with the {self.job_title} role.",
            "good_match": f"Good alignment with the {self.job_title} role.",
            "partial_match": f"Partial alignment with the {self.job_title} role.",
            "low_match": f"Limited alignment with the {self.job_title} role.",
            "insufficient_evidence": (
                f"The resume provides too little evidence to assess alignment "
                f"with the {self.job_title} role."
            ),
        }.get(classification, f"Alignment assessment for the {self.job_title} role.")

        matched = [r["requirement"] for r in skill_results if r["status"] == "match"]
        partial = [r["requirement"] for r in skill_results if r["status"] == "partial"]
        gaps = [r["requirement"] for r in skill_results if r["status"] == "gap"]
        unknown = [r["requirement"] for r in skill_results if r["status"] == "unknown"]

        parts: list[str] = [opener]
        if matched:
            listed = ", ".join(matched[:4])
            more = f" (and {len(matched) - 4} more)" if len(matched) > 4 else ""
            parts.append(
                f"The resume supports {len(matched)} required/preferred skill(s): "
                f"{listed}{more}."
            )
        if partial:
            parts.append(
                "Partial evidence found for: " + ", ".join(partial[:3]) + "."
            )
        if gaps:
            parts.append(
                "Limited or no evidence was found for: " + ", ".join(gaps[:3]) + "."
            )
        if unknown:
            parts.append(
                "The resume does not provide enough information to evaluate: "
                + ", ".join(unknown[:3]) + "."
            )
        ea = experience_alignment
        if ea["required_years"] is not None:
            parts.append(ea["reason"])
        return " ".join(parts)

    # ─── shared result shape ───────────────────────────────────────────

    @staticmethod
    def _result(
        requirement: str,
        category: str | None,
        level: str,
        status: str,
        strength: str,
        reason: str,
        evidence: list[dict[str, Any]],
        requirement_type: str = "skill",
    ) -> dict[str, Any]:
        return {
            "requirement": requirement,
            "requirement_type": requirement_type,
            "level": level,
            "category": category,
            "status": status,
            "evidence_strength": strength,
            "reason": reason,
            "evidence": evidence,
        }


class SkillGapBuilder:
    def __init__(self) -> None:
        self.strengths: list[str] = []
        self.partial: list[str] = []
        self.gaps: list[str] = []
        self.unknown: list[str] = []

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "strengths": self.strengths,
            "partial": self.partial,
            "gaps": self.gaps,
            "unknown": self.unknown,
        }


def build_profile_from_dict(data: dict[str, Any] | None) -> ResumeProfile | None:
    """Safely hydrate a Phase 1 ResumeProfile from stored JSON."""
    if not isinstance(data, dict) or not data:
        return None
    try:
        return ResumeProfile.model_validate(data)
    except Exception:  # noqa: BLE001 — malformed legacy payloads degrade gracefully
        return None


def run_fit_analysis(
    job_title: str,
    requirements: dict[str, Any],
    profile_json: dict[str, Any] | None,
    raw_text: str | None,
) -> dict[str, Any]:
    """Convenience wrapper used by the service layer."""
    profile = build_profile_from_dict(profile_json)
    evidence = CandidateEvidenceIndex(profile, raw_text)
    engine = FitEngine(job_title, requirements, evidence)
    return engine.analyze()
