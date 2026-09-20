"""Scorecard generation engine."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Interview, InterviewEvaluation
from app.repositories.interview.interview import (
    InterviewEvaluationRepository,
    InterviewScorecardRepository,
)


class ScorecardEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.eval_repo = InterviewEvaluationRepository(session)
        self.scorecard_repo = InterviewScorecardRepository(session)

    async def generate_scorecard(
        self,
        interview_id: uuid.UUID,
        recruiter_notes: str | None = None,
    ) -> dict:
        interview = await self.session.get(Interview, interview_id)
        if not interview:
            raise ValueError("Interview not found")

        evaluations = await self.eval_repo.list_by_interview(interview_id)
        if not evaluations:
            raise ValueError("No evaluations found for this interview")

        scores = self._aggregate_scores(evaluations)
        recommendation = self._determine_recommendation(scores["overall_score"])
        hiring_confidence = self._calculate_hiring_confidence(evaluations, scores)
        ai_summary = self._generate_summary(scores, len(evaluations), interview)

        existing = await self.scorecard_repo.get_by_interview(interview_id)
        if existing:
            scorecard = await self.scorecard_repo.update(
                existing.id,
                **scores,
                recommendation=recommendation,
                hiring_confidence=hiring_confidence,
                recruiter_notes=recruiter_notes or existing.recruiter_notes,
                ai_summary=ai_summary,
            )
        else:
            scorecard = await self.scorecard_repo.create(
                interview_id=interview_id,
                **scores,
                recommendation=recommendation,
                hiring_confidence=hiring_confidence,
                recruiter_notes=recruiter_notes,
                ai_summary=ai_summary,
            )

        return {
            "id": scorecard.id,
            "interview_id": interview_id,
            **scores,
            "recommendation": recommendation,
            "hiring_confidence": hiring_confidence,
            "ai_summary": ai_summary,
            "recruiter_notes": recruiter_notes,
        }

    def _aggregate_scores(self, evaluations: list[InterviewEvaluation]) -> dict:
        n = len(evaluations)
        avg_tech = sum(e.technical_accuracy for e in evaluations) / n
        avg_comm = sum(e.communication for e in evaluations) / n
        avg_prob = sum(e.problem_solving for e in evaluations) / n
        avg_comp = sum(e.completeness for e in evaluations) / n
        avg_conf = sum(e.confidence for e in evaluations) / n
        avg_rel = sum(e.relevance for e in evaluations) / n

        technical_skills = round(avg_tech)
        communication = round(avg_comm)
        problem_solving = round(avg_prob)
        teamwork = min(100, round((avg_comm + avg_rel) / 2 + 10))
        leadership = min(100, round((avg_conf + avg_prob) / 2 + 5))
        culture_fit = min(100, round((avg_comm + avg_rel + avg_conf) / 3))
        learning_ability = min(100, round((avg_comp + avg_prob) / 2 + 5))
        overall_score = round(
            technical_skills * 0.25
            + communication * 0.20
            + problem_solving * 0.20
            + teamwork * 0.10
            + leadership * 0.05
            + culture_fit * 0.10
            + learning_ability * 0.10
        )

        return {
            "technical_skills": technical_skills,
            "communication": communication,
            "teamwork": teamwork,
            "leadership": leadership,
            "problem_solving": problem_solving,
            "culture_fit": culture_fit,
            "learning_ability": learning_ability,
            "overall_score": overall_score,
        }

    @staticmethod
    def _determine_recommendation(score: int) -> str:
        if score >= 80:
            return "strongly_recommend"
        elif score >= 65:
            return "recommend"
        elif score >= 45:
            return "consider"
        return "not_recommended"

    @staticmethod
    def _calculate_hiring_confidence(
        evaluations: list[InterviewEvaluation], scores: dict
    ) -> int:
        n = len(evaluations)
        score_variance = 0
        overall = scores["overall_score"]
        for e in evaluations:
            score_variance += (e.overall_score - overall) ** 2
        score_variance = (score_variance / n) ** 0.5 if n > 1 else 0

        confidence = 50
        if overall >= 75:
            confidence += 20
        elif overall >= 55:
            confidence += 10
        elif overall < 40:
            confidence -= 15

        if score_variance < 10:
            confidence += 15
        elif score_variance < 20:
            confidence += 5
        else:
            confidence -= 10

        if n >= 5:
            confidence += 5

        return min(max(confidence, 10), 95)

    @staticmethod
    def _generate_summary(scores: dict, num_evaluations: int, interview: Interview) -> str:
        overall = scores["overall_score"]
        if overall >= 80:
            level = "excellent"
        elif overall >= 65:
            level = "good"
        elif overall >= 45:
            level = "average"
        else:
            level = "below average"

        parts = [f"Candidate demonstrated {level} performance across {num_evaluations} evaluated responses."]

        if scores["technical_skills"] >= 70:
            parts.append("Strong technical skills shown.")
        elif scores["technical_skills"] < 50:
            parts.append("Technical skills need improvement.")

        if scores["communication"] >= 70:
            parts.append("Clear and articulate communication.")
        elif scores["communication"] < 50:
            parts.append("Communication could be more structured.")

        if scores["problem_solving"] >= 70:
            parts.append("Good problem-solving approach demonstrated.")
        elif scores["problem_solving"] < 50:
            parts.append("Problem-solving methodology could be stronger.")

        return " ".join(parts)
