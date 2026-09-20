"""Persistence adapter for Skill2Job profile state (Phase 3)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobProfileState

PROFILE_STATE_VERSION = "skill2job-profile-3.0.0"


class ProfileStateAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> Skill2JobProfileState | None:
        result = await self.session.execute(
            select(Skill2JobProfileState).where(
                Skill2JobProfileState.user_id == user_id
            )
        )
        return result.scalars().first()

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        dossier: dict,
        skill_evidence: dict,
        completeness: dict,
        corrections: list,
    ) -> Skill2JobProfileState:
        state = await self.get(user_id)
        if state is None:
            state = Skill2JobProfileState(
                user_id=user_id,
                scoring_version=PROFILE_STATE_VERSION,
            )
            self.session.add(state)
        state.normalized_profile = dossier
        state.skill_evidence = skill_evidence
        state.completeness = completeness
        state.corrections = corrections
        state.scoring_version = PROFILE_STATE_VERSION
        await self.session.flush()
        return state