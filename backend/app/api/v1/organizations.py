"""Organization management endpoints."""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    require_permission,
    RequireOrgMembership,
)
from app.core.permissions import Permission
from app.domain.models import User
from app.domain.schemas_organization import (
    InvitationCreate,
    InvitationListResponse,
    InvitationResponse,
    MembershipListResponse,
    MembershipUpdateRequest,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationMembershipResponse,
    UserBrief,
)
from app.services.audit_service import AuditService
from app.services.invitation_service import InvitationService
from app.services.organization_service import OrganizationService
from app.repositories.membership import OrganizationMembershipRepository
from app.repositories.organization import OrganizationRepository

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ── Organization CRUD ────────────────────────────────────────────────

@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = OrganizationService(db)
    org = await svc.create_organization(
        name=body.name,
        slug=body.slug,
        creator_id=current_user.id,
        description=body.description,
        official_email=body.official_email,
        domain=body.domain,
    )
    audit = AuditService(db)
    await audit.log("organization_created", "org_create", user_id=current_user.id, details={"org_id": str(org.id), "slug": body.slug})
    return org


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = OrganizationService(db)
    org = await svc.get_organization(organization_id)
    belongs = await svc.check_user_belongs_to_org(current_user.id, organization_id)
    if not belongs:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError(detail="You are not a member of this organization")
    return org


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: uuid.UUID,
    body: OrganizationUpdate,
    current_user: User = Depends(RequireOrgMembership("organization_admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = OrganizationService(db)
    return await svc.update_organization(
        organization_id,
        name=body.name,
        description=body.description,
        official_email=body.official_email,
        domain=body.domain,
    )


@router.get("/me/list", response_model=list[OrganizationResponse])
async def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = OrganizationService(db)
    memberships = await svc.get_user_memberships(current_user.id)
    org_ids = [m.organization_id for m in memberships]
    org_repo = OrganizationRepository(db)
    orgs = await org_repo.get_by_ids(org_ids)
    org_map = {str(o.id): o for o in orgs}
    return [org_map[str(m.organization_id)] for m in memberships if str(m.organization_id) in org_map]


# ── Membership Management ────────────────────────────────────────────

@router.get("/{organization_id}/members", response_model=MembershipListResponse)
async def list_members(
    organization_id: uuid.UUID,
    current_user: User = Depends(RequireOrgMembership("organization_admin", "hr_manager")),
    db: AsyncSession = Depends(get_db),
):
    svc = OrganizationService(db)
    members = await svc.get_org_members(organization_id)
    items = []
    for m in members:
        items.append(OrganizationMembershipResponse(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            role=m.role,
            status=m.status,
            invited_by_id=m.invited_by_id,
            joined_at=m.joined_at,
            created_at=m.created_at,
            user=UserBrief(id=m.user.id, full_name=m.user.full_name, email=m.user.email) if m.user else None,
        ))
    return MembershipListResponse(items=items, total=len(items))


@router.put("/{organization_id}/members/{membership_id}/status")
async def update_member_status(
    request: Request,
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: MembershipUpdateRequest,
    current_user: User = Depends(RequireOrgMembership("organization_admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = OrganizationService(db)
    membership = await svc.update_member_status(
        membership_id,
        body.status,
        actor_id=current_user.id,
        actor_org_role=getattr(request.state, 'membership', None) and request.state.membership.role or "organization_admin",
    )
    audit = AuditService(db)
    await audit.log_membership_change(
        current_user.id, organization_id, f"membership_{body.status}", target_user=membership.user_id,
    )
    return {"message": f"Member status updated to {body.status}"}


# ── Invitation Management ────────────────────────────────────────────

@router.post("/{organization_id}/invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    organization_id: uuid.UUID,
    body: InvitationCreate,
    current_user: User = Depends(RequireOrgMembership("organization_admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = InvitationService(db)
    invitation, raw_token = await svc.create_invitation(
        organization_id=organization_id,
        invited_by_id=current_user.id,
        email=body.email,
        role=body.role,
    )
    audit = AuditService(db)
    await audit.log_invitation_created(current_user.id, organization_id, body.email, body.role)

    # Commit BEFORE queuing email: never send mail for an uncommitted invitation.
    await db.commit()

    from app.notifications.email_tasks import queue_invitation_email
    from app.services.organization_service import OrganizationService as _OrgSvc
    _org_svc = _OrgSvc(db)
    _org = await _org_svc.get_organization(organization_id)

    _email_result = queue_invitation_email(
        to_email=invitation.email,
        invited_by_name=current_user.full_name,
        organization_name=_org.name,
        role=invitation.role,
        raw_token=raw_token,
        expires_at_str=invitation.expires_at.isoformat(),
    )

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        organization_id=invitation.organization_id,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
        email_status=_email_result.get("status", "unknown"),
    )


@router.get("/{organization_id}/invitations", response_model=InvitationListResponse)
async def list_invitations(
    organization_id: uuid.UUID,
    current_user: User = Depends(RequireOrgMembership("organization_admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = InvitationService(db)
    invitations = await svc.list_organization_invitations(organization_id)
    items = [
        InvitationResponse(
            id=i.id, email=i.email, role=i.role, status=i.status,
            organization_id=i.organization_id, expires_at=i.expires_at,
            created_at=i.created_at, accepted_at=i.accepted_at,
        )
        for i in invitations
    ]
    return InvitationListResponse(items=items, total=len(items))


@router.post("/{organization_id}/invitations/{invitation_id}/revoke")
async def revoke_invitation(
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: User = Depends(RequireOrgMembership("organization_admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = InvitationService(db)
    await svc.revoke_invitation(invitation_id, current_user.id)
    audit = AuditService(db)
    await audit.log("invitation_revoked", "invitation_revoke", user_id=current_user.id, organization_id=organization_id, details={"invitation_id": str(invitation_id)})
    return {"message": "Invitation revoked"}


@router.post("/{organization_id}/invitations/{invitation_id}/resend", response_model=InvitationResponse)
async def resend_invitation(
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: User = Depends(RequireOrgMembership("organization_admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = InvitationService(db)
    invitation, raw_token = await svc.resend_invitation(invitation_id, current_user.id)

    # Commit BEFORE queuing email: token rotation must be durable first.
    await db.commit()

    from app.notifications.email_tasks import queue_invitation_email
    from app.services.organization_service import OrganizationService as _OrgSvc
    _org_svc = _OrgSvc(db)
    _org = await _org_svc.get_organization(organization_id)

    _email_result = queue_invitation_email(
        to_email=invitation.email,
        invited_by_name=current_user.full_name,
        organization_name=_org.name,
        role=invitation.role,
        raw_token=raw_token,
        expires_at_str=invitation.expires_at.isoformat(),
    )

    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        organization_id=invitation.organization_id,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
        email_status=_email_result.get("status", "unknown"),
    )
