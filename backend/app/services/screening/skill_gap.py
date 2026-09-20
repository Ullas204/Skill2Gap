from __future__ import annotations

from typing import Any


class SkillGapAnalyzer:
    """Analyses skill, experience, education, and certification gaps
    and produces actionable improvement suggestions for candidates."""

    @staticmethod
    def analyze(
        matched_skills: list[str],
        missing_required: list[str],
        missing_preferred: list[str],
        candidate_experience_years: float,
        required_experience_str: str | None,
        candidate_degrees: list[str],
        required_education: str | None,
        candidate_certs: list[str],
        overall_score: int,
    ) -> dict[str, Any]:
        exp_gap = SkillGapAnalyzer._experience_gap(
            candidate_experience_years, required_experience_str,
        )
        edu_gap = SkillGapAnalyzer._education_gap(
            candidate_degrees, required_education,
        )
        cert_gap = SkillGapAnalyzer._certification_gap(
            candidate_certs, missing_required,
        )
        skill_suggestions = SkillGapAnalyzer._skill_suggestions(
            missing_required, missing_preferred,
        )
        improvement = SkillGapAnalyzer._improvement_suggestions(
            overall_score=overall_score,
            matched_skills=matched_skills,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            exp_gap=exp_gap,
            edu_gap=edu_gap,
            cert_gap=cert_gap,
        )
        readiness = SkillGapAnalyzer._interview_readiness(
            overall_score=overall_score,
            missing_required_count=len(missing_required),
            exp_gap=exp_gap,
        )
        return {
            "missing_required_skills": missing_required,
            "missing_preferred_skills": missing_preferred,
            "experience_gap_description": exp_gap,
            "education_gap_description": edu_gap,
            "certification_gap_description": cert_gap,
            "skill_suggestions": skill_suggestions,
            "improvement_suggestions": improvement,
            "interview_readiness_score": readiness,
        }

    @staticmethod
    def _experience_gap(candidate_years: float, required_str: str | None) -> str | None:
        if not required_str:
            return None
        import re
        nums = re.findall(r"(\d+(?:\.\d+)?)", required_str)
        if not nums:
            return None
        required = max(float(n) for n in nums)
        if candidate_years >= required:
            return None
        diff = required - candidate_years
        if diff <= 1:
            return f"Needs approximately {diff:.0f} more year(s) of experience"
        return f"Needs approximately {diff:.0f} more years of experience (has {candidate_years:.0f}, requires {required:.0f})"

    @staticmethod
    def _education_gap(candidate_degrees: list[str], required_education: str | None) -> str | None:
        if not required_education:
            return None
        if not candidate_degrees:
            return f"Candidate has no formal education recorded; job requires: {required_education}"
        from app.services.screening.matching_engine import MatchingEngine
        req_level = MatchingEngine._degree_level(required_education)
        cand_max = max(MatchingEngine._degree_level(d) for d in candidate_degrees)
        if cand_max >= req_level:
            return None
        return f"Candidate's highest qualification is below the required level ({required_education})"

    @staticmethod
    def _certification_gap(candidate_certs: list[str], missing_required: list[str]) -> str | None:
        if not missing_required:
            return None
        cert_keywords = ["certified", "certification", "certificate", "aws", "azure", "gcp", "cka", "cka"]
        relevant_missing = [s for s in missing_required if any(k in s.lower() for k in cert_keywords)]
        if relevant_missing:
            return f"Consider obtaining: {', '.join(relevant_missing[:3])}"
        return None

    @staticmethod
    def _skill_suggestions(missing_required: list[str], missing_preferred: list[str]) -> list[str]:
        suggestions: list[str] = []
        for skill in missing_required[:5]:
            suggestions.append(f"Learn {skill} — this is a required skill for the role")
        for skill in missing_preferred[:3]:
            suggestions.append(f"Consider learning {skill} — this is a preferred skill")
        return suggestions

    @staticmethod
    def _improvement_suggestions(
        overall_score: int,
        matched_skills: list[str],
        missing_required: list[str],
        missing_preferred: list[str],
        exp_gap: str | None,
        edu_gap: str | None,
        cert_gap: str | None,
    ) -> list[str]:
        suggestions: list[str] = []
        if missing_required:
            suggestions.append(f"Focus on acquiring these required skills: {', '.join(missing_required[:3])}")
        if missing_preferred:
            suggestions.append(f"Adding preferred skills would improve your match: {', '.join(missing_preferred[:3])}")
        if exp_gap:
            suggestions.append("Gain more relevant work experience or highlight transferable experience")
        if edu_gap:
            suggestions.append("Consider pursuing additional education or certifications")
        if cert_gap:
            suggestions.append(cert_gap)
        if matched_skills:
            suggestions.append(f"Highlight your expertise in {', '.join(matched_skills[:3])} during interviews")
        if overall_score < 50:
            suggestions.append("This may not be the best-fit role; consider upskilling before applying")
        elif overall_score < 70:
            suggestions.append("With targeted skill improvements, you could be a stronger candidate")
        if not suggestions:
            suggestions.append("You are a strong fit — prepare for behavioral and technical interviews")
        return suggestions

    @staticmethod
    def _interview_readiness(overall_score: int, missing_required_count: int, exp_gap: str | None) -> int:
        readiness = min(overall_score + 10, 100)
        readiness -= missing_required_count * 5
        if exp_gap:
            readiness -= 10
        return int(max(min(readiness, 100), 0))
