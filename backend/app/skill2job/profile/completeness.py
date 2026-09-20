"""Deterministic profile completeness scoring (Phase 3).

Reuses the platform's ``SECTION_WEIGHTS`` semantics from ProfileService so the
dossier's completeness number is consistent with the recruiter-visible
``profile_completion`` value. No AI claims are added.
"""

from __future__ import annotations

from app.skill2job.profile.schemas import CompletenessSummary

SECTION_WEIGHTS = {
    "personal_info": 25, "education": 20, "experience": 20,
    "skills": 15, "projects": 10, "certifications": 5, "languages": 5,
}
SKILL_MINIMUM = 3


def compute_completeness(
    *,
    has_personal_info: bool,
    education_count: int,
    experience_count: int,
    skill_count: int,
    projects_count: int,
    certifications_count: int,
    languages_count: int,
) -> CompletenessSummary:
    filled = {
        "personal_info": has_personal_info,
        "education": education_count > 0,
        "experience": experience_count > 0,
        "skills": skill_count >= SKILL_MINIMUM,
        "projects": projects_count > 0,
        "certifications": certifications_count > 0,
        "languages": languages_count > 0,
    }
    score = sum(SECTION_WEIGHTS[s] for s, is_filled in filled.items() if is_filled)
    missing = [s for s, is_filled in filled.items() if not is_filled]
    return CompletenessSummary(
        score=score,
        total=sum(SECTION_WEIGHTS.values()),
        filled_sections=[s for s, is_filled in filled.items() if is_filled],
        missing_sections=missing,
    )


def section_label(section: str) -> str:
    return section.replace("_", " ").title()