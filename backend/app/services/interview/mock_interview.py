"""Mock Interview orchestration service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Interview, InterviewQuestion
from app.repositories.interview.interview import (
    InterviewAnswerRepository,
    InterviewQuestionRepository,
    InterviewRepository,
)
from app.services.interview.answer_evaluator import AnswerEvaluator


class MockInterviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.interview_repo = InterviewRepository(session)
        self.question_repo = InterviewQuestionRepository(session)
        self.answer_repo = InterviewAnswerRepository(session)

    async def start_mock(
        self,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        questions: list[dict],
    ) -> Interview:
        interview = await self.interview_repo.create(
            job_id=job_id,
            candidate_id=candidate_id,
            interview_type="mock",
            status="in_progress",
            started_at=datetime.now(timezone.utc),
            total_questions=len(questions),
            questions_answered=0,
        )

        for idx, q in enumerate(questions):
            await self.question_repo.create(
                interview_id=interview.id,
                question_text=q["question_text"],
                category=q["category"],
                difficulty=q["difficulty"],
                order_index=idx,
                context=q.get("context"),
            )

        await self.session.flush()
        return interview

    async def submit_answer(
        self,
        question_id: uuid.UUID,
        answer_text: str,
        time_taken_seconds: int | None = None,
    ) -> dict:
        question = await self.session.get(InterviewQuestion, question_id)
        if not question:
            raise ValueError("Question not found")

        existing = await self.answer_repo.get_by_question(question_id)
        if existing:
            raise ValueError("Answer already submitted for this question")

        answer = await self.answer_repo.create(
            question_id=question_id,
            answer_text=answer_text,
            time_taken_seconds=time_taken_seconds,
        )

        evaluation = AnswerEvaluator.evaluate_answer(
            question_text=question.question_text,
            answer_text=answer_text,
            category=question.category,
            question_context=question.context,
        )

        from app.repositories.interview.interview import InterviewEvaluationRepository
        eval_repo = InterviewEvaluationRepository(self.session)
        await eval_repo.create(
            answer_id=answer.id,
            **evaluation,
        )

        interview = await self.session.get(Interview, question.interview_id)
        if interview:
            interview.questions_answered += 1
            if interview.questions_answered >= interview.total_questions:
                interview.status = "completed"
                interview.completed_at = datetime.now(timezone.utc)

        await self.session.flush()

        next_q = await self.question_repo.get_unanswered(question.interview_id)
        questions_remaining = 0
        if next_q:
            all_q = await self.question_repo.list_by_interview(question.interview_id)
            answered_qs = await self.answer_repo.list_by_interview(question.interview_id)
            answered_ids = {a.question_id for a in answered_qs}
            questions_remaining = sum(1 for q in all_q if q.id not in answered_ids) - 1

        return {
            "answer_id": answer.id,
            "evaluation": evaluation,
            "next_question": next_q,
            "questions_remaining": max(questions_remaining, 0),
        }

    async def complete_interview(self, interview_id: uuid.UUID) -> dict:
        interview = await self.interview_repo.get_with_questions(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        await self.session.flush()

        from app.repositories.interview.interview import InterviewEvaluationRepository
        eval_repo = InterviewEvaluationRepository(self.session)
        evaluations = await eval_repo.list_by_interview(interview_id)

        if not evaluations:
            return {
                "interview_id": interview_id,
                "overall_score": 0,
                "strong_areas": [],
                "weak_areas": [],
                "improvement_suggestions": [],
                "feedback_summary": "No answers were evaluated.",
            }

        avg_scores = {
            "technical_accuracy": sum(e.technical_accuracy for e in evaluations) / len(evaluations),
            "completeness": sum(e.completeness for e in evaluations) / len(evaluations),
            "communication": sum(e.communication for e in evaluations) / len(evaluations),
            "problem_solving": sum(e.problem_solving for e in evaluations) / len(evaluations),
            "confidence": sum(e.confidence for e in evaluations) / len(evaluations),
            "relevance": sum(e.relevance for e in evaluations) / len(evaluations),
        }
        overall = sum(avg_scores.values()) / len(avg_scores)

        strong = [k for k, v in avg_scores.items() if v >= 70]
        weak = [k for k, v in avg_scores.items() if v < 50]

        all_suggestions = []
        for e in evaluations:
            if e.improvement_suggestions:
                all_suggestions.extend(e.improvement_suggestions)
        unique_suggestions = list(dict.fromkeys(all_suggestions))[:5]

        return {
            "interview_id": interview_id,
            "overall_score": round(overall),
            "strong_areas": strong,
            "weak_areas": weak,
            "improvement_suggestions": unique_suggestions,
            "feedback_summary": f"You scored {round(overall)} overall. {'Strong performance!' if overall >= 70 else 'Keep practicing to improve.'}",
        }
