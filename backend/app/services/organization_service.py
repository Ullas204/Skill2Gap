"""Organization and membership management service."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import MembershipStatus, OrganizationStatus, RoleName
from app.domain.models import Organization, OrganizationMembership
from app.repositories.membership import OrganizationMembershipRepository
from app.repositories.organization import OrganizationRepository

logger = get_logger(__name__)

VALID_INVITATION_ROLES = {RoleName.HR_MANAGER.value, RoleName.RECRUITER.value}


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._org_repo = OrganizationRepository(session)
        self._membership_repo = OrganizationMembershipRepository(session)

    async def create_organization(
        self,
        name: str,
        slug: str,
        creator_id: uuid.UUID,
        description: str | None = None,
        official_email: str | None = None,
        domain: str | None = None,
    ) -> Organization:
        existing = await self._org_repo.get_by_slug(slug)
        if existing:
            raise ConflictError(detail="Organization with this slug already exists")

        import re
        if not re.match(r"^[a-z0-9][a-z0-9\-]*$", slug):
            raise ValidationError(detail="Slug must contain only lowercase letters, numbers, and hyphens")

        org = await self._org_repo.create(
            name=name,
            slug=slug,
            description=description,
            official_email=official_email,
            domain=domain,
            status=OrganizationStatus.ACTIVE.value,
        )

        membership = OrganizationMembership(
            user_id=creator_id,
            organization_id=org.id,
            role=RoleName.ORG_ADMIN.value,
            status=MembershipStatus.ACTIVE.value,
            joined_at=datetime.now(timezone.utc),
        )
        self._session.add(membership)
        await self._session.flush()

        logger.info("Organization created: id=%s slug=%s creator=%s", org.id, slug, creator_id)
        return org

    async def get_organization(self, org_id: uuid.UUID) -> Organization:
        org = await self._org_repo.get(org_id)
        if not org:
            raise NotFoundError(detail="Organization not found")
        return org

    async def get_organization_by_slug(self, slug: str) -> Organization:
        org = await self._org_repo.get_by_slug(slug)
        if not org:
            raise NotFoundError(detail="Organization not found")
        return org

    async def update_organization(
        self,
        org_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        official_email: str | None = None,
        domain: str | None = None,
    ) -> Organization:
        org = await self._org_repo.get(org_id)
        if not org:
            raise NotFoundError(detail="Organization not found")
        if name is not None:
            org.name = name
        if description is not None:
            org.description = description
        if official_email is not None:
            org.official_email = official_email
        if domain is not None:
            org.domain = domain
        await self._session.flush()
        await self._session.refresh(org)
        return org

    async def get_user_memberships(self, user_id: uuid.UUID) -> list[OrganizationMembership]:
        return await self._membership_repo.get_user_organizations(user_id)

    async def get_org_members(
        self, organization_id: uuid.UUID, include_inactive: bool = False
    ) -> list[OrganizationMembership]:
        return await self._membership_repo.get_org_members(organization_id, include_inactive)

    async def get_org_member_count(self, organization_id: uuid.UUID) -> int:
        return await self._membership_repo.count_org_members(organization_id)

    async def update_member_status(
        self,
        membership_id: uuid.UUID,
        status: str,
        actor_id: uuid.UUID,
        actor_org_role: str,
    ) -> OrganizationMembership:
        if actor_org_role not in {RoleName.ORG_ADMIN.value}:
            raise ForbiddenError(detail="Only organization admin can modify membership status")

        valid_statuses = {
            MembershipStatus.ACTIVE.value,
            MembershipStatus.SUSPENDED.value,
            MembershipStatus.REVOKED.value,
        }
        if status not in valid_statuses:
            raise ValidationError(detail=f"Invalid status: {status}")

        membership = await self._membership_repo.get(membership_id)
        if not membership:
            raise NotFoundError(detail="Membership not found")

        if membership.user_id == actor_id:
            raise ValidationError(detail="Cannot modify your own membership")

        await self._membership_repo.update_status(membership_id, status)
        return await self._membership_repo.get(membership_id)

    async def check_user_belongs_to_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> bool:
        membership = await self._membership_repo.get_active_membership(user_id, organization_id)
        return membership is not None

    async def check_user_has_role_in_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, *roles: str
    ) -> bool:
        membership = await self._membership_repo.get_active_membership(user_id, organization_id)
        if not membership:
            return False
        return membership.role in roles

    async def get_user_role_in_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> str | None:
        membership = await self._membership_repo.get_active_membership(user_id, organization_id)
        return membership.role if membership else None
