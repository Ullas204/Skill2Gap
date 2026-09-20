"""Phase 12 – Assessment Platform API endpoints.

Every endpoint is protected by the platform RBAC layer:
* hr / recruiter   – build, browse and analyze assessments
* candidate        – take assessments, run code, view own results
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.assessment_schemas import (
    AnalyticsResponse,
    AnswerResultResponse,
    AnswerSubmitRequest,
    AssessmentCreateRequest,
    AssessmentListResponse,
    AssessmentResponse,
    AttemptListItem,
    AttemptListResponse,
    AttemptStartResponse,
    CodeRunRequest,
    CodeRunResponse,
    IntegrityEventRequest,
    ResultResponse,
    TestResultOut,
)
from app.domain.models import User
from app.services.assessment.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _get_service(db: AsyncSession = Depends(get_db)) -> AssessmentService:
    return AssessmentService(db)


def _map_error(e: ValueError) -> HTTPException:
    msg = str(e)
    status = {
        "NO_ATTEMPTS_REMAINING": 409,
        "ALREADY_ANSWERED": 409,
    }.get(msg, None)
    if msg.startswith("ATTEMPT_"):
        status = 409
    elif msg in {"Assessment not found", "Attempt not found", "Question not found", "Job not found"}:
        status = 404
    return HTTPException(status_code=status or 400, detail=msg)


# ═══ Recruiter: build & browse ══════════════════════════════════


@router.post("/generate", response_model=AssessmentResponse)
async def generate_assessment(
    body: AssessmentCreateRequest,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        assessment = await service.create_assessment(current_user.id, body)
    except ValueError as e:
        raise _map_error(e)
    items, total = await service.list_assessments()
    out = next(a for a in items if a["id"] == assessment.id)
    return AssessmentResponse(**out)


@router.get("", response_model=AssessmentListResponse)
async def list_assessments(
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    items, total = await service.list_assessments()
    return AssessmentListResponse(items=[AssessmentResponse(**a) for a in items], total=total)


@router.get("/me", response_model=AttemptListResponse)
async def my_attempts(
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    data = await service.my_attempts(current_user.id)
    return AttemptListResponse(items=[AttemptListItem(**i) for i in data["items"]], total=data["total"])


# ═══ Candidate: take ════════════════════════════════════════════


@router.post("/{assessment_id}/start", response_model=AttemptStartResponse)
async def start_attempt(
    assessment_id: uuid.UUID,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        return AttemptStartResponse(**await service.start_attempt(assessment_id, current_user.id))
    except ValueError as e:
        raise _map_error(e)


@router.get("/attempts/{attempt_id}", response_model=dict)
async def attempt_state(
    attempt_id: uuid.UUID,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        return await service.get_attempt_state(attempt_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your attempt")
    except ValueError as e:
        raise _map_error(e)


@router.post("/{attempt_id}/answer", response_model=AnswerResultResponse)
async def submit_answer(
    attempt_id: uuid.UUID,
    body: AnswerSubmitRequest,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        data = await service.submit_answer(
            attempt_id, current_user.id, body.question_id, body.answer, body.time_taken_seconds,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your attempt")
    except ValueError as e:
        raise _map_error(e)
    from app.domain.assessment_schemas import EvaluationOut, QuestionPublic
    return AnswerResultResponse(
        answer_id=data["answer_id"],
        evaluation=EvaluationOut(**data["evaluation"]),
        correct_answer_revealed=data["correct_answer_revealed"],
        explanation=data["explanation"],
        next_question=QuestionPublic(**data["next_question"]) if data["next_question"] else None,
        questions_remaining=data["questions_remaining"],
        progress=data["progress"],
    )


@router.post("/{attempt_id}/code/run", response_model=CodeRunResponse)
async def run_code(
    attempt_id: uuid.UUID,
    body: CodeRunRequest,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        run = await service.run_code(attempt_id, current_user.id, body.question_id, body.language, body.code)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your attempt")
    except ValueError as e:
        raise _map_error(e)
    return CodeRunResponse(
        ok=run.get("ok", False),
        stdout=str(run.get("stdout", "")),
        stderr=str(run.get("stderr", "")),
        execution_time_ms=int(run.get("execution_time_ms", 0)),
        passed_count=int(run.get("passed_count", 0)),
        total_count=int(run.get("total_count", 0)),
        test_results=[TestResultOut(**t) for t in run.get("test_results", [])],
        timed_out=bool(run.get("timed_out")),
        sandbox_mode=str(run.get("sandbox_mode", "local")),
    )


@router.post("/{attempt_id}/code/submit", response_model=AnswerResultResponse)
async def submit_code(
    attempt_id: uuid.UUID,
    body: CodeRunRequest,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        data = await service.submit_answer(
            attempt_id, current_user.id, body.question_id,
            {"code": body.code, "language": body.language}, None,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your attempt")
    except ValueError as e:
        raise _map_error(e)
    from app.domain.assessment_schemas import EvaluationOut, QuestionPublic
    return AnswerResultResponse(
        answer_id=data["answer_id"],
        evaluation=EvaluationOut(**data["evaluation"]),
        correct_answer_revealed=False,
        explanation=None,
        next_question=QuestionPublic(**data["next_question"]) if data["next_question"] else None,
        questions_remaining=data["questions_remaining"],
        progress=data["progress"],
    )


@router.post("/{attempt_id}/integrity", response_model=dict)
async def integrity_event(
    attempt_id: uuid.UUID,
    body: IntegrityEventRequest,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        await service.record_integrity_event(attempt_id, current_user.id, body.event_type, body.detail)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your attempt")
    except ValueError as e:
        raise _map_error(e)
    return {"message": "Event recorded"}


@router.post("/{attempt_id}/submit", response_model=ResultResponse)
async def finalize_attempt(
    attempt_id: uuid.UUID,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        # Ownership check without grading side effects.
        await service._own_attempt(attempt_id, current_user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your attempt")
    except ValueError as e:
        raise _map_error(e)
    result = await service.finalize(attempt_id)
    return ResultResponse(**result)


@router.get("/{attempt_id}/result", response_model=ResultResponse)
async def get_result(
    attempt_id: uuid.UUID,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate", "hr", "recruiter")),
):
    result = await service.get_result(attempt_id)
    user_roles = {ur.role.name for ur in current_user.roles}
    if str(result["candidate_id"]) != str(current_user.id) and not (user_roles & {"hr_manager", "recruiter", "admin", "super_admin", "organization_admin"}):
        raise HTTPException(status_code=403, detail="Not your result")
    return ResultResponse(**result)


# ═══ Staff: detail & analytics ══════════════════════════════════


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: uuid.UUID,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    items, _total = await service.list_assessments()
    match = next((a for a in items if a["id"] == assessment_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return AssessmentResponse(**match)


@router.get("/{assessment_id}/analytics", response_model=AnalyticsResponse)
async def assessment_analytics(
    assessment_id: uuid.UUID,
    service: AssessmentService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        return AnalyticsResponse(**await service.analytics(assessment_id))
    except ValueError as e:
        raise _map_error(e)
