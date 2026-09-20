"""Phase 5 — Recruiter Invitation System tests.

Extends the Phase 4 architecture (no second service/endpoint set). Covers:
- Authorization matrix: who may invite recruiters
- Role escalation protection at schema level
- Duplicate invitation / duplicate membership handling
- New-recruiter acceptance flow (account + membership + global role)
- Existing-user signed-in acceptance flow
- Email identity enforcement (mismatch rejected)
- Token lifecycle: expired / revoked / tampered / resend rotation
- Single-use consumption (double accept)
- Cross-tenant safety: organization derived from invitation only
- Email content requirements for recruiter invitations (template + queue)
"""

import uuid
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.domain.models import Invitation, OrganizationMembership, Role, User, UserRole
from app.domain.enums import InvitationStatus, MembershipStatus

PASSWORD = "SecureP@ss1"


# ═══════════════════════════════════════════════════════════════════
# HELPERS (mirroring Phase 4 test scaffolding)
# ═══════════════════════════════════════════════════════════════════


async def _create_user_with_role_in_db(session, email: str, name: str, role_name: str, password: str = PASSWORD) -> User:
    user = User(
        id=uuid.uuid4(),
        full_name=name,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    role = (
        await session.execute(select(Role).where(Role.name == role_name))
    ).scalar_one_or_none()
    if role:
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.flush()
    await session.refresh(user)
    return user


async def _create_org_membership(session, user_id, org_id, role="organization_admin"):
    membership = OrganizationMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        organization_id=org_id,
        role=role,
        status=MembershipStatus.ACTIVE.value,
        joined_at=datetime.now(timezone.utc),
    )
    session.add(membership)
    await session.flush()
    return membership


async def _login(client: AsyncClient, email: str, password: str = PASSWORD) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _setup_org_with_admin(client: AsyncClient, session, name="Recruiter Org") -> tuple[str, str, uuid.UUID]:
    """Create admin user, create org via API. Returns (token, org_id, admin_user_id)."""
    user = await _create_user_with_role_in_db(session, f"adm_{uuid.uuid4().hex[:8]}@test.com", "Org Admin", "admin")
    token = await _login(client, user.email)
    resp = await client.post(
        "/api/v1/organizations",
        json={"name": name, "slug": f"rec-org-{uuid.uuid4().hex[:8]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return token, resp.json()["id"], user.id


async def _invite_via_api(client: AsyncClient, token: str, org_id: str, email: str, role: str = "recruiter"):
    return await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {token}"},
    )


async def _seed_recruiter_invitation(session, org_id: str, invited_by, email: str, **overrides) -> tuple[Invitation, str]:
    """Insert a pending recruiter invitation directly; returns (row, raw_token)."""
    raw_token = Invitation.generate_token()
    kwargs = dict(
        organization_id=uuid.UUID(org_id) if isinstance(org_id, str) else org_id,
        invited_by_id=invited_by,
        email=email,
        role="recruiter",
        token_hash=Invitation.hash_token(raw_token),
        status=InvitationStatus.PENDING.value,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    kwargs.update(overrides)
    invitation = Invitation(**kwargs)
    session.add(invitation)
    await session.flush()
    return invitation, raw_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════
# 1. AUTHORIZATION — who may invite recruiters
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_org_admin_can_invite_recruiter(client: AsyncClient, session):
    with patch("app.notifications.email_tasks.queue_invitation_email") as mock_queue:
        mock_queue.return_value = {"status": "queued", "task_id": "t"}
        token, org_id, _ = await _setup_org_with_admin(client, session)
        resp = await _invite_via_api(client, token, org_id, f"rec_{uuid.uuid4().hex[:6]}@example.com")

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "recruiter"
    assert body["status"] == InvitationStatus.PENDING.value
    # Raw token material never leaves the server via API responses
    assert "token" not in body and "token_hash" not in body


@pytest.mark.asyncio
async def test_hr_manager_cannot_invite_recruiter(client: AsyncClient, session):
    token, org_id, _ = await _setup_org_with_admin(client, session)
    hr = await _create_user_with_role_in_db(session, f"hr_{uuid.uuid4().hex[:6]}@test.com", "HR", "hr_manager")
    await _create_org_membership(session, hr.id, uuid.UUID(org_id), "hr_manager")
    hr_token = await _login(client, hr.email)

    resp = await _invite_via_api(client, hr_token, org_id, "victim@example.com")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_recruiter_member_cannot_invite_recruiter(client: AsyncClient, session):
    token, org_id, _ = await _setup_org_with_admin(client, session)
    rec = await _create_user_with_role_in_db(session, f"rec_{uuid.uuid4().hex[:6]}@test.com", "Rec", "recruiter")
    await _create_org_membership(session, rec.id, uuid.UUID(org_id), "recruiter")
    rec_token = await _login(client, rec.email)

    resp = await _invite_via_api(client, rec_token, org_id, "someone@example.com")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_invite_recruiter(client: AsyncClient, session):
    _, org_id, _ = await _setup_org_with_admin(client, session)
    resp = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "x@example.com", "role": "recruiter"},
    )
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_admin_of_org_a_cannot_invite_into_org_b(client: AsyncClient, session):
    token_a, _, _ = await _setup_org_with_admin(client, session, name="Org A")
    _, org_b, _ = await _setup_org_with_admin(client, session, name="Org B")

    resp = await _invite_via_api(client, token_a, org_b, "cross@example.com")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_invite_recruiter(client: AsyncClient, session):
    _, org_id, _ = await _setup_org_with_admin(client, session)
    outsider = await _create_user_with_role_in_db(session, f"out_{uuid.uuid4().hex[:6]}@test.com", "Out", "admin")
    out_token = await _login(client, outsider.email)

    resp = await _invite_via_api(client, out_token, org_id, "nomem@example.com")
    assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════
# 2. ROLE ESCALATION — server-side validation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_role", ["admin", "super_admin", "platform_admin", "candidate", "owner", "", "DROP TABLE"])
async def test_escalated_roles_rejected_at_schema_level(client: AsyncClient, session, bad_role):
    token, org_id, _ = await _setup_org_with_admin(client, session)
    resp = await _invite_via_api(client, token, org_id, "esc@example.com", role=bad_role)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════
# 3. DUPLICATES
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_duplicate_pending_invitation_returns_conflict(client: AsyncClient, session):
    token, org_id, _ = await _setup_org_with_admin(client, session)
    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"

    with patch("app.notifications.email_tasks.queue_invitation_email") as mock_queue:
        mock_queue.return_value = {"status": "queued", "task_id": "t1"}
        first = await _invite_via_api(client, token, org_id, email)
    assert first.status_code == 201

    with patch("app.notifications.email_tasks.queue_invitation_email") as mock_queue:
        mock_queue.return_value = {"status": "queued", "task_id": "t2"}
        second = await _invite_via_api(client, token, org_id, email.upper())
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_existing_member_cannot_be_invited_again(client: AsyncClient, session):
    token, org_id, _ = await _setup_org_with_admin(client, session)
    existing = await _create_user_with_role_in_db(session, f"mem_{uuid.uuid4().hex[:6]}@example.com", "Member", "recruiter")
    await _create_org_membership(session, existing.id, uuid.UUID(org_id), "recruiter")

    resp = await _invite_via_api(client, token, org_id, existing.email)
    assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════════════
# 4. ACCEPTANCE — new recruiter account creation
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_new_recruiter_validate_response_shape(client: AsyncClient, session):
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    email = f"shape_{uuid.uuid4().hex[:6]}@example.com"
    _, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, email)

    validate = await client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert validate.status_code == 200
    body = validate.json()
    assert body["valid"] is True
    assert body["role"] == "recruiter"
    assert body["email"] == email
    assert body["organization_name"]
    assert body["existing_user"] is False
    assert "token_hash" not in body


@pytest.mark.asyncio
async def test_new_recruiter_acceptance_full_flow(client: AsyncClient, session):
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    email = f"newrec_{uuid.uuid4().hex[:6]}@example.com"
    invitation, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, email)

    accept = await client.post(
        "/api/v1/invitations/accept",
        json={
            "token": raw_token,
            "full_name": "New Recruiter",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        },
    )
    assert accept.status_code == 200, accept.text

    # Account exists exactly once with recruiter global role
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one()
    role_names = (
        await session.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        )
    ).scalars().all()
    assert "recruiter" in role_names

    # Membership scoped to the invited organization with recruiter role
    mem = (
        await session.execute(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
    ).scalar_one()
    assert str(mem.organization_id) == str(org_id)
    assert mem.role == "recruiter"
    assert mem.status == MembershipStatus.ACTIVE.value

    # Invitation consumed
    await session.refresh(invitation)
    assert invitation.status == InvitationStatus.ACCEPTED.value
    assert invitation.accepted_at is not None


@pytest.mark.asyncio
async def test_acceptance_token_is_single_use(client: AsyncClient, session):
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    email = f"reuse_{uuid.uuid4().hex[:6]}@example.com"
    _, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, email)

    first = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "full_name": "A", "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "full_name": "B", "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert second.status_code in (400, 409, 410, 422)


# ═══════════════════════════════════════════════════════════════════
# 5. ACCEPTANCE — existing user account
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_existing_user_accepts_via_sign_in_flow(client: AsyncClient, session):
    token, org_id, admin_id = await _setup_org_with_admin(client, session)
    email = f"exists_{uuid.uuid4().hex[:6]}@example.com"
    existing = await _create_user_with_role_in_db(session, email, "Exists", "candidate")
    user_token = await _login(client, email)

    _, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, email)

    validate = await client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert validate.json()["existing_user"] is True

    resp = await client.post(
        "/api/v1/invitations/accept-signed-in",
        json={"token": raw_token},
        headers=_auth(user_token),
    )
    assert resp.status_code == 200, resp.text

    mem = (
        await session.execute(
            select(OrganizationMembership).where(OrganizationMembership.user_id == existing.id)
        )
    ).scalar_one()
    assert mem.role == "recruiter"
    assert str(mem.organization_id) == str(org_id)


@pytest.mark.asyncio
async def test_email_mismatch_rejected_for_signed_in_acceptance(client: AsyncClient, session):
    token, org_id, admin_id = await _setup_org_with_admin(client, session)
    bob = await _create_user_with_role_in_db(session, f"bob_{uuid.uuid4().hex[:6]}@example.com", "Bob", "candidate")
    bob_token = await _login(client, bob.email)

    alice_email = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    invitation, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, alice_email)

    resp = await client.post(
        "/api/v1/invitations/accept-signed-in",
        json={"token": raw_token},
        headers=_auth(bob_token),
    )
    assert resp.status_code == 403

    # Alice's invitation must remain pending and unconsumed
    await session.refresh(invitation)
    assert invitation.status == InvitationStatus.PENDING.value
    assert invitation.accepted_at is None


@pytest.mark.asyncio
async def test_new_user_endpoint_rejects_email_with_existing_account(client: AsyncClient, session):
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    taken_email = f"taken_{uuid.uuid4().hex[:6]}@example.com"
    await _create_user_with_role_in_db(session, taken_email, "Taken", "candidate")

    _, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, taken_email)
    resp = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "full_name": "X", "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert resp.status_code in (409, 422)


# ═══════════════════════════════════════════════════════════════════
# 6. TOKEN LIFECYCLE
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_tampered_token_rejected(client: AsyncClient, session):
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    _, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, "tamper@example.com")
    bad = raw_token[:-2] + ("xx" if not raw_token.endswith("xx") else "yy")

    validate = await client.get(f"/api/v1/invitations/validate/{bad}")
    assert validate.json()["valid"] is False

    accept = await client.post(
        "/api/v1/invitations/accept",
        json={"token": bad, "full_name": "T", "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert accept.status_code in (404, 410, 422)


@pytest.mark.asyncio
async def test_expired_recruiter_invitation_rejected(client: AsyncClient, session):
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    invitation, raw_token = await _seed_recruiter_invitation(
        session, org_id, admin_id, "expired@example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    validate = await client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert validate.json()["valid"] is False

    accept = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "full_name": "T", "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert accept.status_code in (400, 409, 410, 422)


@pytest.mark.asyncio
async def test_revoked_recruiter_invitation_rejected(client: AsyncClient, session):
    token, org_id, admin_id = await _setup_org_with_admin(client, session)
    invitation, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, "revoked@example.com")

    revoke = await client.post(
        f"/api/v1/organizations/{org_id}/invitations/{invitation.id}/revoke",
        headers=_auth(token),
    )
    assert revoke.status_code == 200

    validate = await client.get(f"/api/v1/invitations/validate/{raw_token}")
    assert validate.json()["valid"] is False


@pytest.mark.asyncio
async def test_hr_manager_cannot_revoke_or_resend(client: AsyncClient, session):
    token, org_id, admin_id = await _setup_org_with_admin(client, session)
    hr = await _create_user_with_role_in_db(session, f"hr2_{uuid.uuid4().hex[:6]}@test.com", "HR", "hr_manager")
    await _create_org_membership(session, hr.id, uuid.UUID(org_id), "hr_manager")
    hr_token = await _login(client, hr.email)

    invitation, _ = await _seed_recruiter_invitation(session, org_id, admin_id, "guard@example.com")

    revoke = await client.post(
        f"/api/v1/organizations/{org_id}/invitations/{invitation.id}/revoke",
        headers=_auth(hr_token),
    )
    assert revoke.status_code == 403

    with patch("app.notifications.email_tasks.queue_invitation_email") as mock_queue:
        mock_queue.return_value = {"status": "queued", "task_id": "t"}
        resend = await client.post(
            f"/api/v1/organizations/{org_id}/invitations/{invitation.id}/resend",
            headers=_auth(hr_token),
        )
    assert resend.status_code == 403


@pytest.mark.asyncio
async def test_resend_rotates_hash_and_invalidates_old_token(client: AsyncClient, session):
    token, org_id, admin_id = await _setup_org_with_admin(client, session)
    invitation, old_raw = await _seed_recruiter_invitation(session, org_id, admin_id, "rotate@example.com")
    old_hash = invitation.token_hash
    old_expiry = invitation.expires_at

    with patch("app.notifications.email_tasks.queue_invitation_email") as mock_queue:
        mock_queue.return_value = {"status": "queued", "task_id": "rot"}
        resend = await client.post(
            f"/api/v1/organizations/{org_id}/invitations/{invitation.id}/resend",
            headers=_auth(token),
        )
    assert resend.status_code == 200, resend.text
    assert resend.json()["status"] == InvitationStatus.PENDING.value

    # Old raw token must no longer validate; hash rotated in DB; expiry bumped.
    assert (await client.get(f"/api/v1/invitations/validate/{old_raw}")).json()["valid"] is False

    await session.refresh(invitation)
    assert invitation.token_hash != old_hash
    # Expiry resets to the service's configured window; SQLite stores naive datetimes.
    from app.services.invitation_service import InvitationService
    assert InvitationService._as_aware_utc(invitation.expires_at) > datetime.now(timezone.utc)
    assert invitation.status == InvitationStatus.PENDING.value


@pytest.mark.asyncio
async def test_double_accept_concurrent_style_single_consumption(client: AsyncClient, session):
    """Two sequential accepts with the same token — exactly one account created."""
    _, org_id, admin_id = await _setup_org_with_admin(client, session)
    email = f"race_{uuid.uuid4().hex[:6]}@example.com"
    _, raw_token = await _seed_recruiter_invitation(session, org_id, admin_id, email)

    payload = {"token": raw_token, "full_name": "Racer", "password": PASSWORD, "confirm_password": PASSWORD}
    r1 = await client.post("/api/v1/invitations/accept", json=payload)
    r2 = await client.post("/api/v1/invitations/accept", json=payload)

    statuses = {r1.status_code, r2.status_code}
    assert 200 in statuses
    assert any(s in (400, 409, 410, 422) for s in statuses)

    users = (
        await session.execute(select(User).where(User.email == email))
    ).scalars().all()
    assert len(users) == 1


# ═══════════════════════════════════════════════════════════════════
# 7. CROSS-TENANT SAFETY
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_membership_always_lands_in_invited_organization(client: AsyncClient, session):
    """Acceptance derives organization from the invitation — no client org input exists."""
    _, org_a, admin_a = await _setup_org_with_admin(client, session, name="Tenant A")
    _, org_b, _ = await _setup_org_with_admin(client, session, name="Tenant B")

    email = f"tenant_{uuid.uuid4().hex[:6]}@example.com"
    _, raw_token = await _seed_recruiter_invitation(session, org_a, admin_a, email)

    resp = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "full_name": "T", "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert resp.status_code == 200

    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one()
    mems = (
        await session.execute(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
    ).scalars().all()

    assert len(mems) == 1
    assert str(mems[0].organization_id) == str(org_a)
    assert all(str(m.organization_id) != str(org_b) for m in mems)


# ═══════════════════════════════════════════════════════════════════
# 8. EMAIL CONTENT — recruiter invitations
# ═══════════════════════════════════════════════════════════════════


def test_recruiter_email_template_contains_required_content():
    from app.services.email_service import EmailService

    svc = EmailService()
    html = svc.render_template(
        "invitation_email.html",
        invited_by_name="John Smith",
        organization_name="Acme Corporation",
        role_label="Recruiter",
        accept_url="https://hirecraft.ai/invite/tok123",
        expires_at="2026-09-01",
        app_name="AI Hiring Copilot",
    )
    assert "John Smith" in html          # inviter
    assert "Acme Corporation" in html    # organization
    assert "Recruiter" in html           # role label
    assert "2026-09-01" in html          # expiry
    assert "/invite/tok123" in html      # CTA link
    assert "token_hash" not in html      # internal fields never leak
    assert "eyJ" not in html             # no JWT fragments


def test_role_labels_cover_recruiter_for_email():
    from app.notifications.email_tasks import ROLE_LABELS

    assert ROLE_LABELS["recruiter"] == "Recruiter"


@pytest.mark.asyncio
async def test_recruiter_invite_queues_email_with_correct_params(client: AsyncClient, session):
    with patch("app.notifications.email_tasks.queue_invitation_email") as mock_queue:
        mock_queue.return_value = {"status": "queued", "task_id": "abc"}
        token, org_id, admin_id = await _setup_org_with_admin(client, session)
        org_resp = await client.get(f"/api/v1/organizations/{org_id}", headers=_auth(token))
        org_name = org_resp.json()["name"]

        resp = await _invite_via_api(client, token, org_id, "queued@example.com")

    assert resp.status_code == 201
    assert resp.json()["email_status"] == "queued"
    mock_queue.assert_called_once()
    kwargs = mock_queue.call_args.kwargs
    assert kwargs["to_email"] == "queued@example.com"
    assert kwargs["organization_name"] == org_name
    assert kwargs["role"] == "recruiter"
    assert kwargs["expires_at_str"]
