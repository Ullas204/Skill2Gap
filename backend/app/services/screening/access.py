"""Typed access-control errors + server-side authorization for screening reads."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    Job,
    JobApplication,
    OrganizationMembership,
    User,
)


class JobNotFoundError(ValueError):
    pass


class JobAccessDeniedError(PermissionError):
    pass


class CandidateNotAccessibleError(PermissionError):
    pass


# Roles that may read job-scoped intelligence within their organization.
_ORG_READ_ROLES = {"recruiter", "hr", "hr_manager", "organization_admin", "admin"}


async def authorize_job_access(
    session: AsyncSession, job_id: uuid.UUID, user: User,
) -> Job:
    """Return the job if ``user`` may access it, otherwise raise.

    Allowed: the recruiter who owns the job, or an active member of the
    job's organization holding one of ``_ORG_READ_ROLES``. This is enforced
    server-side regardless of frontend filtering.
    """
    job = await session.get(Job, job_id)
    if not job:
        raise JobNotFoundError("Job not found")

    if job.recruiter_id == user.id:
        return job

    if job.organization_id is not None:
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == job.organization_id,
        )
        membership = (await session.execute(stmt)).scalar_one_or_none()
        if membership and membership.role in _ORG_READ_ROLES:
            return job

    raise JobAccessDeniedError("You do not have access to this job")


async def authorize_candidate_access(
    session: AsyncSession, candidate_id: uuid.UUID, user: User,
) -> None:
    """Raise unless ``user`` may read candidate-scoped intelligence.

    A recruiter/HR may view candidate-level intelligence only when the
    candidate applied to at least one job they can access (owned by them or
    shared through their organization with a read role). Enforced
    server-side regardless of frontend filtering.
    """
    org_ids = select(OrganizationMembership.organization_id).where(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.role.in_(_ORG_READ_ROLES),
    )
    stmt = (
        select(JobApplication.id)
        .join(Job, JobApplication.job_id == Job.id)
        .where(JobApplication.candidate_id == candidate_id)
        .where(
            or_(
                Job.recruiter_id == user.id,
                Job.organization_id.in_(org_ids),
            )
        )
        .limit(1)
    )
    application_id = (await session.execute(stmt)).scalar_one_or_none()
    if application_id is None:
        raise CandidateNotAccessibleError(
            "You do not have access to this candidate"
        )
