import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import (
    CodingAssessment,
    Interview,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewScorecard,
)
from app.repositories.base import BaseRepository


class InterviewRepository(BaseRepository[Interview]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Interview)

    async def get_with_questions(self, interview_id: uuid.UUID) -> Interview | None:
        stmt = (
            select(Interview)
            .options(selectinload(Interview.questions).selectinload(InterviewQuestion.answer).selectinload(InterviewAnswer.evaluation))
            .options(selectinload(Interview.scorecard))
            .where(Interview.id == interview_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_candidate(self, candidate_id: uuid.UUID) -> list[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.candidate_id == candidate_id)
            .order_by(Interview.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_recruiter(self, recruiter_id: uuid.UUID) -> list[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.recruiter_id == recruiter_id)
            .order_by(Interview.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_job(self, job_id: uuid.UUID) -> list[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.job_id == job_id)
            .order_by(Interview.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_upcoming_by_candidate(self, candidate_id: uuid.UUID) -> list[Interview]:
        from datetime import datetime, timezone
        stmt = (
            select(Interview)
            .where(
                Interview.candidate_id == candidate_id,
                Interview.status.in_(["scheduled", "in_progress"]),
                Interview.scheduled_at >= datetime.now(timezone.utc),
            )
            .order_by(Interview.scheduled_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_upcoming_by_recruiter(self, recruiter_id: uuid.UUID) -> list[Interview]:
        from datetime import datetime, timezone
        stmt = (
            select(Interview)
            .where(
                Interview.recruiter_id == recruiter_id,
                Interview.status.in_(["scheduled", "in_progress"]),
                Interview.scheduled_at >= datetime.now(timezone.utc),
            )
            .order_by(Interview.scheduled_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_completed(self, candidate_id: uuid.UUID | None = None, recruiter_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count(Interview.id)).where(Interview.status == "completed")
        if candidate_id:
            stmt = stmt.where(Interview.candidate_id == candidate_id)
        if recruiter_id:
            stmt = stmt.where(Interview.recruiter_id == recruiter_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def avg_score(self, candidate_id: uuid.UUID | None = None) -> float:
        from sqlalchemy import and_
        stmt = (
            select(func.avg(InterviewScorecard.overall_score))
            .join(Interview, InterviewScorecard.interview_id == Interview.id)
            .where(Interview.status == "completed")
        )
        if candidate_id:
            stmt = stmt.where(Interview.candidate_id == candidate_id)
        result = await self._session.execute(stmt)
        avg = result.scalar_one()
        return float(avg) if avg else 0.0

    async def count_total(self, candidate_id: uuid.UUID | None = None, recruiter_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count(Interview.id))
        if candidate_id:
            stmt = stmt.where(Interview.candidate_id == candidate_id)
        if recruiter_id:
            stmt = stmt.where(Interview.recruiter_id == recruiter_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()


class InterviewQuestionRepository(BaseRepository[InterviewQuestion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InterviewQuestion)

    async def list_by_interview(self, interview_id: uuid.UUID) -> list[InterviewQuestion]:
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview_id)
            .order_by(InterviewQuestion.order_index)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_unanswered(self, interview_id: uuid.UUID) -> InterviewQuestion | None:
        stmt = (
            select(InterviewQuestion)
            .outerjoin(InterviewAnswer, InterviewQuestion.id == InterviewAnswer.question_id)
            .where(
                InterviewQuestion.interview_id == interview_id,
                InterviewAnswer.id.is_(None),
            )
            .order_by(InterviewQuestion.order_index)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class InterviewAnswerRepository(BaseRepository[InterviewAnswer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InterviewAnswer)

    async def get_by_question(self, question_id: uuid.UUID) -> InterviewAnswer | None:
        stmt = select(InterviewAnswer).where(InterviewAnswer.question_id == question_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_interview(self, interview_id: uuid.UUID) -> list[InterviewAnswer]:
        stmt = (
            select(InterviewAnswer)
            .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
            .where(InterviewQuestion.interview_id == interview_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class InterviewEvaluationRepository(BaseRepository[InterviewEvaluation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InterviewEvaluation)

    async def get_by_answer(self, answer_id: uuid.UUID) -> InterviewEvaluation | None:
        stmt = select(InterviewEvaluation).where(InterviewEvaluation.answer_id == answer_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_interview(self, interview_id: uuid.UUID) -> list[InterviewEvaluation]:
        stmt = (
            select(InterviewEvaluation)
            .join(InterviewAnswer, InterviewEvaluation.answer_id == InterviewAnswer.id)
            .join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id)
            .where(InterviewQuestion.interview_id == interview_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class InterviewScorecardRepository(BaseRepository[InterviewScorecard]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InterviewScorecard)

    async def get_by_interview(self, interview_id: uuid.UUID) -> InterviewScorecard | None:
        stmt = select(InterviewScorecard).where(InterviewScorecard.interview_id == interview_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_candidate(self, candidate_id: uuid.UUID) -> list[InterviewScorecard]:
        stmt = (
            select(InterviewScorecard)
            .join(Interview, InterviewScorecard.interview_id == Interview.id)
            .where(Interview.candidate_id == candidate_id)
            .order_by(InterviewScorecard.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class CodingAssessmentRepository(BaseRepository[CodingAssessment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CodingAssessment)

    async def list_by_interview(self, interview_id: uuid.UUID) -> list[CodingAssessment]:
        stmt = (
            select(CodingAssessment)
            .where(CodingAssessment.interview_id == interview_id)
            .order_by(CodingAssessment.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
