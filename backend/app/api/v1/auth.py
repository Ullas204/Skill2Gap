from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_service, get_current_user, get_db, get_user_repo
from app.domain.models import User
from app.domain.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RoleListResponse,
    TokenRefresh,
    TokenResponse,
    UserResponse,
    OrganizationMembershipBrief,
)
from app.repositories.user import UserRepository
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, auth: AuthService = Depends(get_auth_service)):
    return await auth.register(body.full_name, body.email, body.password)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    return await auth.login(body.email, body.password, remember_me=body.remember_me)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: TokenRefresh, auth: AuthService = Depends(get_auth_service)):
    return await auth.refresh(body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: TokenRefresh | None = None,
    current_user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
):
    refresh_token = body.refresh_token if body else None
    await auth.logout(str(current_user.id), refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.repositories.membership import OrganizationMembershipRepository
    membership_repo = OrganizationMembershipRepository(db)
    memberships = await membership_repo.get_user_organizations(current_user.id)

    membership_briefs = []
    for m in memberships:
        org_name = m.organization.name if m.organization else "Unknown"
        membership_briefs.append(OrganizationMembershipBrief(
            id=m.id,
            organization_id=m.organization_id,
            organization_name=org_name,
            role=m.role,
            status=m.status,
        ))

    roles = [ur.role.name for ur in current_user.roles]
    return UserResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        roles=roles,
        organization_memberships=membership_briefs,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.get("/roles", response_model=list[RoleListResponse])
async def list_roles(user_repo: UserRepository = Depends(get_user_repo)):
    roles = await user_repo.list_roles()
    return [RoleListResponse(id=r.id, name=r.name, description=r.description) for r in roles]
