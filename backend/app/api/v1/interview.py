import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.interview_schemas import (
    CodingAssessmentGenerateRequest,
    CodingAssessmentResponse,
    CodingSubmissionRequest,
    CodingSubmissionResponse,
    InterviewAnswerRequest,
    InterviewCompleteRequest,
    InterviewDashboardResponse,
    InterviewDetailResponse,
    InterviewGenerateRequest,
    InterviewGenerateResponse,
    InterviewListResponse,
    InterviewNotesRequest,
    InterviewScheduleRequest,
    InterviewStartRequest,
    MockInterviewStartResponse,
    AnswerSubmitResponse,
    ScorecardCreateRequest,
    ScorecardResponse,
    CandidateInterviewDashboardResponse,
)
from app.domain.models import User
from app.services.interview.coding_engine import CodingEngine
from app.services.interview.interview_analytics import InterviewAnalytics
from app.services.interview.interview_service import InterviewService
from app.services.interview.mock_interview import MockInterviewService

router = APIRouter(prefix="/interview", tags=["interview"])


def _get_service(db: AsyncSession = Depends(get_db)) -> InterviewService:
    return InterviewService(db)


def _get_analytics(db: AsyncSession = Depends(get_db)) -> InterviewAnalytics:
    return InterviewAnalytics(db)


# ─── Generate Questions ────────────────────────────────────────────


@router.post("/generate", response_model=InterviewGenerateResponse)
async def generate_questions(
    body: InterviewGenerateRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        result = await service.generate_questions(
            job_id=body.job_id,
            recruiter_id=current_user.id,
            categories=body.categories,
            difficulty=body.difficulty,
            count=body.count,
            candidate_id=body.candidate_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    from app.domain.interview_schemas import QuestionResponse
    questions = [
        QuestionResponse(
            id=uuid.uuid4(),
            question_text=q["question_text"],
            category=q["category"],
            difficulty=q["difficulty"],
            order_index=idx,
            context=q.get("context"),
        )
        for idx, q in enumerate(result["questions"])
    ]

    return InterviewGenerateResponse(
        interview_id=uuid.uuid4(),
        questions=questions,
        total_questions=result["total_questions"],
        categories=result["categories"],
        difficulty=result["difficulty"],
    )


# ─── Schedule Interview ────────────────────────────────────────────


@router.post("/schedule")
async def schedule_interview(
    body: InterviewScheduleRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        interview = await service.schedule_interview(
            job_id=body.job_id,
            candidate_id=body.candidate_id,
            recruiter_id=current_user.id,
            scheduled_at=body.scheduled_at,
            duration_minutes=body.duration_minutes,
            categories=body.categories,
            difficulty=body.difficulty,
            question_count=body.question_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "message": "Interview scheduled successfully",
        "interview_id": str(interview.id),
        "status": interview.status,
    }


# ─── Start Mock Interview ─────────────────────────────────────────


@router.post("/mock/start", response_model=MockInterviewStartResponse)
async def start_mock_interview(
    body: InterviewStartRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    from app.domain.models import Job
    from app.db.session import async_session_factory

    interview = await service.session.get(Job, body.interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        from app.domain.interview_schemas import QuestionResponse
        result = await service.start_mock_interview(
            candidate_id=current_user.id,
            job_id=body.interview_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    first = result["first_question"]
    first_q = QuestionResponse(
        id=first.id,
        question_text=first.question_text,
        category=first.category,
        difficulty=first.difficulty,
        order_index=first.order_index,
        context=first.context,
    ) if first else QuestionResponse(
        id=uuid.uuid4(),
        question_text="No questions available",
        category="technical",
        difficulty="medium",
        order_index=0,
    )

    return MockInterviewStartResponse(
        interview_id=result["interview_id"],
        job_id=result["job_id"],
        job_title=result["job_title"],
        first_question=first_q,
        total_questions=result["total_questions"],
        message="Mock interview started. Answer each question to proceed.",
    )


# ─── Submit Answer ─────────────────────────────────────────────────


@router.post("/mock/answer", response_model=AnswerSubmitResponse)
async def submit_answer(
    body: InterviewAnswerRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    from app.domain.interview_schemas import EvaluationResponse, QuestionResponse
    try:
        result = await service.submit_answer(
            question_id=body.question_id,
            answer_text=body.answer_text,
            time_taken_seconds=body.time_taken_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    eval_data = result["evaluation"]
    evaluation = EvaluationResponse(id=result["answer_id"], **eval_data)

    next_q = None
    if result["next_question"]:
        nq = result["next_question"]
        next_q = QuestionResponse(
            id=nq.id,
            question_text=nq.question_text,
            category=nq.category,
            difficulty=nq.difficulty,
            order_index=nq.order_index,
            context=nq.context,
        )

    return AnswerSubmitResponse(
        answer_id=result["answer_id"],
        evaluation=evaluation,
        next_question=next_q,
        questions_remaining=result["questions_remaining"],
    )


# ─── Complete Mock Interview ──────────────────────────────────────


@router.post("/mock/complete")
async def complete_mock_interview(
    body: InterviewCompleteRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        result = await service.complete_interview(body.interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "interview_id": str(result["interview_id"]),
        "overall_score": result["overall_score"],
        "strong_areas": result["strong_areas"],
        "weak_areas": result["weak_areas"],
        "improvement_suggestions": result["improvement_suggestions"],
        "feedback_summary": result["feedback_summary"],
    }


# ─── List Interviews ──────────────────────────────────────────────


@router.get("/list", response_model=InterviewListResponse)
async def list_interviews(
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate", "hr", "recruiter")),
):
    role = current_user.roles[0].role.name if current_user.roles else "candidate"
    items = await service.list_interviews(current_user.id, role)
    return InterviewListResponse(items=items, total=len(items))


# ─── Dashboard ────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_dashboard(
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate", "hr", "recruiter")),
):
    role = current_user.roles[0].role.name if current_user.roles else "candidate"
    return await service.get_dashboard(current_user.id, role)


# ─── Analytics ────────────────────────────────────────────────────


@router.get("/analytics")
async def get_analytics(
    service: InterviewAnalytics = Depends(_get_analytics),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    role = current_user.roles[0].role.name if current_user.roles else "recruiter"
    recruiter_id = current_user.id if role == "recruiter" else None
    return await service.get_analytics(recruiter_id=recruiter_id)


# ─── Candidate Scorecards ─────────────────────────────────────────


@router.get("/scorecard/{candidate_id}")
async def get_candidate_scorecards(
    candidate_id: uuid.UUID,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    return await service.get_candidate_scorecards(candidate_id)


# ─── Get Interview Detail ─────────────────────────────────────────


@router.get("/{interview_id}")
async def get_interview(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate", "hr", "recruiter")),
):
    result = await service.get_interview_detail(interview_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interview not found")

    role = current_user.roles[0].role.name if current_user.roles else "candidate"
    if role == "candidate" and str(result["candidate_id"]) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "recruiter" and result["recruiter_id"] and str(result["recruiter_id"]) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return result


# ─── Evaluate Interview ───────────────────────────────────────────


@router.post("/{interview_id}/evaluate")
async def evaluate_interview(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        scorecard = await service.evaluate_interview(interview_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return scorecard


# ─── Get Scorecard ────────────────────────────────────────────────


@router.get("/{interview_id}/scorecard")
async def get_scorecard(
    interview_id: uuid.UUID,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate", "hr", "recruiter")),
):
    scorecard = await service.get_scorecard(interview_id)
    if not scorecard:
        raise HTTPException(status_code=404, detail="Scorecard not found")
    return scorecard


# ─── Create/Update Scorecard ──────────────────────────────────────


@router.post("/{interview_id}/scorecard")
async def create_scorecard(
    interview_id: uuid.UUID,
    body: ScorecardCreateRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        scorecard = await service.create_scorecard(
            interview_id=interview_id,
            recruiter_id=current_user.id,
            data=body.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return scorecard


# ─── Add Notes ────────────────────────────────────────────────────


@router.post("/{interview_id}/notes")
async def add_notes(
    interview_id: uuid.UUID,
    body: InterviewNotesRequest,
    service: InterviewService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        await service.add_notes(interview_id, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Notes saved successfully"}


# ─── Coding Assessment ────────────────────────────────────────────


@router.post("/coding/generate")
async def generate_coding_assessment(
    body: CodingAssessmentGenerateRequest,
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    problems = CodingEngine.generate_assessments(
        difficulty=body.difficulty,
        category=body.category,
        count=body.count,
    )
    return {
        "interview_id": str(body.interview_id),
        "assessments": problems,
        "total": len(problems),
    }


@router.post("/coding/submit", response_model=CodingSubmissionResponse)
async def submit_coding_solution(
    body: CodingSubmissionRequest,
    current_user: User = Depends(require_role("candidate")),
):
    from app.domain.models import CodingAssessment
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        assessment = await session.get(CodingAssessment, body.assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        result = CodingEngine.evaluate_submission(
            solution=body.solution,
            test_cases=assessment.test_cases or [],
            category=assessment.category,
        )

        assessment.candidate_solution = body.solution
        assessment.is_correct = result["is_correct"]
        assessment.score = result["score"]
        await session.commit()

    return CodingSubmissionResponse(
        assessment_id=body.assessment_id,
        is_correct=result["is_correct"],
        score=result["score"],
        feedback=result["feedback"],
        expected_approach=result["expected_approach"],
    )
