"""Public invitation endpoints (validate/accept require no prior auth context)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.domain.models import User
from app.domain.schemas_organization import (
    InvitationAcceptRequest,
    InvitationValidateResponse,
    SignedInInvitationAcceptRequest,
)
from app.services.audit_service import AuditService
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("/validate/{token}", response_model=InvitationValidateResponse)
async def validate_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    svc = InvitationService(db)
    try:
        invitation = await svc.validate_invitation(token)
        from app.services.organization_service import OrganizationService
        from app.repositories.user import UserRepository

        org_svc = OrganizationService(db)
        org = await org_svc.get_organization(invitation.organization_id)
        user_repo = UserRepository(db)
        existing_user = await user_repo.get_by_email(invitation.email) is not None
        return InvitationValidateResponse(
            valid=True,
            email=invitation.email,
            role=invitation.role,
            organization_name=org.name,
            expires_at=invitation.expires_at,
            status=invitation.status,
            existing_user=existing_user,
        )
    except Exception:
        return InvitationValidateResponse(valid=False)


@router.post("/accept")
async def accept_invitation(
    body: InvitationAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """New-user acceptance: creates the account bound to the invited email."""
    svc = InvitationService(db)
    membership = await svc.accept_invitation(
        token=body.token,
        full_name=body.full_name,
        password=body.password,
        confirm_password=body.confirm_password,
    )
    audit = AuditService(db)
    await audit.log_invitation_accepted(membership.user_id, membership.organization_id)
    return {"message": "Invitation accepted successfully. You can now log in."}


@router.post("/accept-signed-in")
async def accept_invitation_signed_in(
    body: SignedInInvitationAcceptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Existing-user acceptance: requires sign-in; backend enforces email match."""
    svc = InvitationService(db)
    membership = await svc.accept_invitation_signed_in(body.token, current_user)
    audit = AuditService(db)
    await audit.log_invitation_accepted(membership.user_id, membership.organization_id)
    return {
        "message": "Invitation accepted successfully.",
        "organization_id": str(membership.organization_id),
        "role": membership.role,
    }
