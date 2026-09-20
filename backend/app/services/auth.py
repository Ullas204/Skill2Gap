import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError, ForbiddenError, ValidationError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.domain.enums import AccountStatus, AuditEventType
from app.domain.models import User
from app.domain.schemas import TokenResponse, TokenUserInfo, UserResponse, OrganizationMembershipBrief
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository

logger = get_logger(__name__)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._session = session

    async def _audit(self, event_type: str, action: str, user_id=None, org_id=None, details=None, success=True, ip=None) -> None:
        if self._session:
            try:
                from app.services.audit_service import AuditService
                svc = AuditService(self._session)
                await svc.log(event_type, action, user_id=user_id, organization_id=org_id, details=details, success=success, ip_address=ip)
            except Exception:
                logger.debug("Audit logging failed (non-critical)")

    async def _get_membership_briefs(self, user: User) -> list[OrganizationMembershipBrief]:
        from app.repositories.membership import OrganizationMembershipRepository
        if not self._session:
            return []
        try:
            membership_repo = OrganizationMembershipRepository(self._session)
            memberships = await membership_repo.get_user_organizations(user.id)
            result = []
            for m in memberships:
                org_name = m.organization.name if m.organization else "Unknown"
                result.append(OrganizationMembershipBrief(
                    id=m.id,
                    organization_id=m.organization_id,
                    organization_name=org_name,
                    role=m.role,
                    status=m.status,
                ))
            return result
        except Exception:
            return []

    # ── Registration ────────────────────────────────────────────────

    async def register(
        self,
        full_name: str,
        email: str,
        password: str,
    ) -> UserResponse:
        email = email.strip().lower()
        full_name = full_name.strip()
        logger.info("Registration attempt for email=%s (candidate only)", email)

        existing = await self._user_repo.get_by_email(email)
        if existing:
            logger.warning("Registration failed: email already registered=%s", email)
            raise ConflictError(detail="Email already registered")

        violations = validate_password_strength(password)
        if violations:
            raise ValidationError(
                detail="Password does not meet security requirements",
                extra={"requirements": violations},
            )

        user = await self._user_repo.create(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_verified=False,
            account_status=AccountStatus.ACTIVE.value,
        )

        assigned_role = await self._user_repo.find_role_by_name("candidate")
        if assigned_role:
            await self._user_repo.assign_role(user.id, assigned_role.id)

        user = await self._user_repo.get_with_roles(user.id)

        await self._audit(
            AuditEventType.REGISTER.value, "user_register",
            user_id=user.id, details={"email": email, "role": "candidate"},
        )

        logger.info("Registration successful: user_id=%s email=%s role=candidate", user.id, email)
        return self._to_user_response(user)

    # ── Login ───────────────────────────────────────────────────────

    async def login(
        self, email: str, password: str, remember_me: bool = False,
    ) -> TokenResponse:
        email = email.strip().lower()
        logger.info("Login attempt for email=%s", email)

        user = await self._user_repo.get_by_email_with_roles(email)
        if not user or not verify_password(password, user.password_hash):
            logger.warning("Login failed: invalid credentials email=%s", email)
            await self._audit(
                AuditEventType.LOGIN_FAILED.value, "login_failed",
                details={"email": email, "reason": "invalid_credentials"}, success=False,
            )
            raise UnauthorizedError(detail="Invalid email or password")

        if not user.is_active:
            logger.warning("Login failed: disabled account email=%s", email)
            await self._audit(
                AuditEventType.LOGIN_FAILED.value, "login_failed",
                user_id=user.id, details={"reason": "account_disabled"}, success=False,
            )
            raise UnauthorizedError(detail="Account has been disabled. Contact your administrator.")

        if user.account_status and user.account_status not in (
            AccountStatus.ACTIVE.value, AccountStatus.PENDING_VERIFICATION.value,
        ):
            logger.warning("Login failed: account_status=%s email=%s", user.account_status, email)
            await self._audit(
                AuditEventType.LOGIN_FAILED.value, "login_failed",
                user_id=user.id, details={"reason": f"account_status_{user.account_status}"}, success=False,
            )
            raise UnauthorizedError(detail=f"Account is {user.account_status}. Contact your administrator.")

        roles = [ur.role.name for ur in user.roles]
        access_token = create_access_token(
            str(user.id),
            roles,
            email=user.email,
            full_name=user.full_name,
        )
        refresh_token = create_refresh_token(str(user.id), remember_me=remember_me)

        if self._refresh_token_repo:
            from app.core.config import get_settings
            settings = get_settings()
            expiry_days = 30 if remember_me else settings.refresh_token_expire_days
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
            await self._refresh_token_repo.store(user.id, refresh_token, expires_at)

        await self._audit(
            AuditEventType.LOGIN.value, "user_login", user_id=user.id,
        )

        membership_briefs = await self._get_membership_briefs(user)

        logger.info("Login successful: user_id=%s email=%s roles=%s", user.id, email, roles)
        user_info = TokenUserInfo(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=roles,
            organization_memberships=membership_briefs,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user_info)

    # ── Refresh ─────────────────────────────────────────────────────

    async def refresh(self, refresh_token_str: str) -> TokenResponse:
        logger.info("Token refresh attempt")

        try:
            payload = decode_token(refresh_token_str)
        except ValueError:
            logger.warning("Token refresh failed: invalid token")
            raise UnauthorizedError(detail="Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            logger.warning("Token refresh failed: invalid token type")
            raise UnauthorizedError(detail="Invalid token type")

        if self._refresh_token_repo:
            is_valid = await self._refresh_token_repo.is_valid(refresh_token_str)
            if not is_valid:
                logger.warning("Token refresh failed: token revoked or expired in DB")
                raise UnauthorizedError(detail="Session has expired. Please sign in again.")

        user_id = payload.get("sub")
        user = await self._user_repo.get_with_roles(uuid.UUID(user_id))
        if not user or not user.is_active:
            logger.warning("Token refresh failed: user not found or inactive user_id=%s", user_id)
            raise UnauthorizedError(detail="User not found or account is disabled")

        if user.account_status and user.account_status not in (
            AccountStatus.ACTIVE.value, AccountStatus.PENDING_VERIFICATION.value,
        ):
            raise UnauthorizedError(detail=f"Account is {user.account_status}")

        roles = [ur.role.name for ur in user.roles]
        new_access = create_access_token(
            str(user.id), roles, email=user.email, full_name=user.full_name,
        )
        new_refresh = create_refresh_token(str(user.id))

        if self._refresh_token_repo:
            await self._refresh_token_repo.revoke(refresh_token_str)
            from app.core.config import get_settings
            settings = get_settings()
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
            await self._refresh_token_repo.store(user.id, new_refresh, expires_at)

        await self._audit(
            AuditEventType.TOKEN_REFRESH.value, "token_refresh", user_id=user.id,
        )

        membership_briefs = await self._get_membership_briefs(user)

        logger.info("Token refresh successful: user_id=%s", user.id)
        user_info = TokenUserInfo(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=roles,
            organization_memberships=membership_briefs,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        return TokenResponse(access_token=new_access, refresh_token=new_refresh, user=user_info)

    # ── Logout ──────────────────────────────────────────────────────

    async def logout(self, user_id: str, refresh_token: str | None = None) -> None:
        logger.info("Logout for user_id=%s", user_id)
        if self._refresh_token_repo and refresh_token:
            await self._refresh_token_repo.revoke(refresh_token)
        await self._audit(
            AuditEventType.LOGOUT.value, "user_logout", user_id=uuid.UUID(user_id),
        )

    async def logout_all(self, user_id: str) -> None:
        logger.info("Logout all sessions for user_id=%s", user_id)
        if self._refresh_token_repo:
            await self._refresh_token_repo.revoke_all_for_user(uuid.UUID(user_id))
        await self._audit(
            AuditEventType.LOGOUT_ALL.value, "logout_all", user_id=uuid.UUID(user_id),
        )

    # ── Current User ────────────────────────────────────────────────

    async def get_current_user(self, user_id: str) -> User:
        user = await self._user_repo.get_with_roles(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise UnauthorizedError(detail="User not found or inactive")
        return user

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _to_user_response(user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=[ur.role.name for ur in user.roles],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
