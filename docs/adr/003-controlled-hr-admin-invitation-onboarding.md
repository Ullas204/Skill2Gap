# ADR-003: Controlled HR / Admin Invitation Onboarding

## Status

Accepted

## Date

2026-08-20

## Context

After restricting public registration to the `candidate` role only (ADR-002), the organization admin must have a controlled mechanism to onboard HR managers and other organization administrators. The invitation system (created in Phase 2) must be tightened to enforce:

1. Only `hr_manager` and `organization_admin` roles can be invited (not `recruiter`, `candidate`, or `super_admin`).
2. Invitations must be email-normalized and secured with high-entropy tokens.
3. Acceptance must support both new users (who register during acceptance) and existing users (who are added as org members).
4. Resend capability must be available for expired or pending invitations.
5. Duplicate membership prevention must be enforced.

## Decision

### Restricted Invitation Roles

- `VALID_INVITABLE_ROLES` in `invitation_service.py` is set to `{hr_manager, organization_admin}`.
- `recruiter` was removed from valid invitation roles — recruiters are onboarded through HR workflows, not direct invitation.
- `candidate`, `super_admin`, `admin` are rejected at the schema level with 422 Unprocessable Entity.
- `InvitationCreate.role` is typed as `Literal["hr_manager", "organization_admin"]` — Pydantic validates before reaching the service layer.

### Email Normalization on Invitations

- `InvitationCreate` schema applies `@field_validator` to normalize email: `v.strip().lower()`.
- `InvitationService.create_invitation()` applies defense-in-depth normalization: `email.strip().lower()`.
- This ensures `HR@Company.com` and `hr@company.com` are treated as the same invitation target.

### Token Security

- `Invitation.generate_token()` uses `secrets.token_urlsafe(48)` — 64+ character tokens with high entropy.
- Only the SHA-256 hash is stored in the database (`Invitation.hash_token()`).
- Raw token is returned once in the API response and never stored.
- Token validation hashes the incoming token and compares against the stored hash.

### Invitation Lifecycle

```
  Admin creates invitation
            │
            ▼
    ┌──── PENDING ────┐
    │                 │
    ▼                 ▼
ACCEPTED           EXPIRED
    │                 │
    ▼                 ▼
Member created    Admin can resend
                  (generates new token)
```

- **Pending**: Token valid, awaiting acceptance. Expires after 7 days.
- **Accepted**: User accepted, membership created. Token becomes single-use.
- **Expired**: Past expiry date. Admin can resend (generates new token, resets expiry).
- **Revoked**: Admin explicitly revoked. Cannot be accepted or resent.

### Acceptance Flow — New User

1. Client validates token via `GET /invitations/validate/{token}`.
2. Client submits `POST /invitations/accept` with `token`, `full_name`, `password`, `confirm_password`.
3. Service creates a new `User` account with the invited role.
4. Service creates an `OrganizationMembership` linking the user to the organization.
5. Invitation status changes to `accepted`.

### Acceptance Flow — Existing User

1. Same validation step.
2. Service finds existing user by email (matching the invitation email).
3. Service creates `OrganizationMembership` for the existing user.
4. No new account is created — existing user gains org access.
5. Invitation status changes to `accepted`.

### Resend Capability

- `POST /organizations/{org_id}/invitations/{invitation_id}/resend`
- Only organization admins can resend.
- Generates a new high-entropy token, resets expiry to 7 days.
- Old token is invalidated (new hash replaces old).
- Available for both `pending` (re-send) and `expired` (re-activate) invitations.

### Duplicate Prevention

- Cannot invite a user who is already an active member of the organization (409 Conflict).
- Cannot invite the same email twice with a pending invitation (409 Conflict).
- Email normalization ensures `User@Org.com` and `user@org.com` are caught as duplicates.

### Cross-Organization Protection

- Non-members cannot create invitations for an organization (403 Forbidden).
- `RequireOrgMembership` dependency enforces tenant isolation on all invitation endpoints.
- Invitation tokens are org-scoped — an invitation for Org A cannot be used to join Org B.

### Frontend Changes

- `TeamManagement.tsx` role selector shows only `hr_manager` and `organization_admin` (no `recruiter`).
- Resend button available for pending/expired invitations.
- `resendInvitation()` API function added to `auth.ts`.

## Consequences

### Positive

- Privileged roles (`hr_manager`, `organization_admin`) are exclusively invitation-controlled.
- `recruiter` role cannot be directly invited — prevents unauthorized recruiter onboarding.
- Email normalization prevents duplicate invitations from case variations.
- Token security (SHA-256 hash only, high entropy) prevents brute-force token guessing.
- Single-use invitations prevent replay attacks.
- Resend capability handles expired invitations without creating duplicate invitations.
- Cross-org isolation ensures invitations are org-scoped.
- 37 new tests covering authorization, role escalation, mass assignment, token security, lifecycle, and backward compatibility.

### Negative

- `recruiter` role cannot be directly invited — must be assigned through HR workflows (intentional restriction).
- Existing users who accept invitations must have the same email as the invitation — no email forwarding.

### Neutral

- Invitation expiry is configurable via `INVITATION_EXPIRY_DAYS` (default: 7).
- Token length is fixed at 64 characters (`secrets.token_urlsafe(48)`).
- Acceptance flow supports both new and existing users without separate endpoints.

## References

- `backend/app/services/invitation_service.py` — InvitationService, VALID_INVITABLE_ROLES
- `backend/app/domain/models.py` — Invitation model (generate_token, hash_token)
- `backend/app/domain/schemas_organization.py` — InvitationCreate, InvitationAcceptRequest
- `backend/app/api/v1/organizations.py` — Invitation CRUD + resend endpoint
- `backend/app/api/v1/invitations.py` — Public validate/accept endpoints
- `frontend/src/pages/TeamManagement.tsx` — Role selector + Resend button
- `frontend/src/api/auth.ts` — resendInvitation() function
- `backend/tests/test_phase4_invitation.py` — invitation security tests

---

# Amendment 1 (2026-08-23): Email Notification + Signed-In Acceptance

## Status

Accepted (amends ADR-003)

## Context

The original decision allowed existing users to accept an invitation by submitting
the token with a name/password payload; the password was silently ignored for
existing accounts. This violated identity enforcement: possession of the token
alone attached organization membership without proving control of the account.
Additionally, the invitation was not emailed at all, and the email queue happened
before the database transaction committed.

## Decisions

### Email Notification via Existing Celery Infrastructure

- Invitation creation queues `send_invitation_email` through the existing Celery
  worker (`app/workers/tasks.py`) and Redis broker; no new mail infrastructure.
- **Commit-before-queue**: both create and resend endpoints call `await db.commit()`
  BEFORE `queue_invitation_email(...)`. An email is never dispatched for an
  uncommitted invitation (and token rotation is durable before the new link ships).
- The Celery task receives only: recipient email, inviter name, org name, role
  label, accept URL, expiry string. No tokens hashes, passwords, or JWTs.
- If Redis/broker is unreachable, a development-only synchronous fallback sends
  directly and reports `email_status` (`queued | sent | skipped | error`) in the API
  response so the UI can distinguish "invitation created" from "email delivered".
- HTML template: `app/notifications/templates/invitation_email.html`, rendered via
  Jinja2 autoescaping; CTA points to `{FRONTEND_BASE_URL}/invite/{token}` only —
  no user-supplied redirect/callback URLs are honored (open-redirect protection).

### Identity Enforcement for Existing Users

- `GET /invitations/validate/{token}` now returns `existing_user: bool`.
- New endpoint `POST /invitations/accept-signed-in` (Bearer auth required):
  - Backend verifies `authenticated_user.email == invitation.email` (403 otherwise).
  - Creates membership + marks invitation accepted atomically.
- `POST /invitations/accept` now REJECTS invitations whose email already has an
  account (422) instead of silently attaching membership. Account creation is only
  possible for emails with no existing account.

### Atomic Single-Use Consumption

- `InvitationRepository.mark_accepted_if_pending()` performs a conditional
  `UPDATE ... WHERE status = 'pending'` and inspects rowcount; concurrent
  acceptance races produce exactly one winner (loser gets 409).
- Membership insert IntegrityError is mapped to 409 (duplicate membership).

### Configurable Expiry

- `INVITATION_EXPIRATION_HOURS` setting (default 72) replaces the hard-coded
  7-day constant. Applied to both creation and resend.

### Canonical Frontend Route

- The email CTA target `/invite/:token` is now the canonical frontend route;
  `/invite/accept/:token` remains as a legacy alias. Previously the CTA pointed to
  a route that did not exist (404).
- Login honors a same-app `?redirect=` parameter (relative paths only —
  open-redirect safe) so existing users return to the invitation after signing in.

## Consequences

- Existing-user tests that accepted via the public endpoint were rewritten for the
  signed-in flow; new tests cover email mismatch (403), double consumption,
  and expiry configuration.
- Email delivery is asynchronous and best-effort: delivery status is separate from
  invitation status (`pending/accepted/expired/revoked`). Resend retries delivery.

---

# Amendment 2 (2026-08-23): Recruiter Added as Invitable Role (Phase 5)

## Status

Accepted (amends ADR-003; supersedes the original "no recruiter invitations"
restriction)

## Context

The original decision excluded `recruiter` from invitable roles on the grounds
that recruiters are onboarded through HR workflows. In practice this blocked the
primary growth path for staffing teams: organization admins had no self-service
way to add recruiters, and no recruiter-onboarding workflow existed. The
invitation infrastructure from Phase 4 (hashed single-use tokens, email
delivery, signed-in acceptance, atomic consumption) is fully role-agnostic.

## Decision

- Add `recruiter` to the server-side invitation allowlists:
  - `InvitationCreate.role: Literal["hr_manager", "organization_admin", "recruiter"]`
    (`app/domain/schemas_organization.py`) — schema validation returns 422 for
    any other role value.
  - `VALID_INVITABLE_ROLES` in `app/services/invitation_service.py`.
- Authorization is unchanged: **only organization admins** may create, resend,
  or revoke invitations of any role, including recruiter. HR managers and
  recruiters still cannot invite anyone. This is the Phase 5 minimum rule;
  per-role invite permissions may be revisited in a later phase.
- Frontend: Team Management invite form gains the Recruiter option (now the
  default), reusing the existing table labels/colors.
- No migration required: the membership/invitation role column is a plain string;
  the global `recruiter` Role row already exists in seed data.
- Acceptance behavior is identical to other roles: new users get account +
  active org membership + global `recruiter` UserRole (idempotent); existing
  users accept via the signed-in endpoint with email enforcement; tokens are
  hashed, single-use, expiring per `INVITATION_EXPIRATION_HOURS`, rotated on
  resend.

## Consequences

- `test_phase4_invitation.py::test_recruiter_role_rejected_for_invitation`
  was rewritten as `test_recruiter_role_accepted_for_invitation` (201).
- New suite `tests/test_phase5_recruiter_invitation.py` (31 tests) covers the
  authorization matrix, escalation rejection, duplicates, both acceptance
  flows, token lifecycle (expired/revoked/tampered/resend rotation/single-use),
  cross-tenant safety, and email content requirements.
- Recruiters onboarded by invitation land directly on the recruiter dashboard;
  route guards already recognize the `recruiter` tier (Phase 4 equivalence map).
