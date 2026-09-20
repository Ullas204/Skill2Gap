# ADR-002: Candidate-Only Public Registration

## Status

Accepted

## Date

2026-08-20

## Context

Public registration must be restricted to the `candidate` role only. All privileged roles (`super_admin`, `organization_admin`, `hr_manager`, `recruiter`) must be granted exclusively through invitation from an organization admin or platform super admin. This prevents privilege escalation via the public registration endpoint.

Additionally, email addresses must be normalized (lowercased and trimmed) to prevent duplicate accounts from case variations (e.g., `User@Example.com` vs `user@example.com`).

## Decision

### Registration is Candidate-Only

- `RegisterRequest` schema accepts only `full_name`, `email`, and `password` — no `role` field.
- `AuthService.register()` hardcodes `role = "candidate"` via `find_role_by_name("candidate")`.
- Frontend `Register.tsx` renders "Create candidate account" with no role selector.
- Any `role` field sent in the JSON body is silently ignored by Pydantic (extra fields are not in the schema).
- Privileged roles require invitation from an organization admin via the `/invitations` endpoint.

### Email Normalization

- `RegisterRequest` and `LoginRequest` schemas apply `@field_validator` to normalize email: `v.strip().lower()`.
- `AuthService.register()` and `AuthService.login()` apply defense-in-depth normalization: `email.strip().lower()`.
- This ensures `User@Example.com` and `user@example.com` are treated as the same account.
- Case-insensitive duplicate detection at the schema level prevents duplicates before they reach the DB.

### Password Security

- Passwords are hashed with bcrypt before storage.
- `UserResponse` and `TokenUserInfo` schemas never include `password_hash`.
- Password strength validation enforces: 8+ chars, uppercase, lowercase, digit.
- API returns 422 for weak passwords with specific requirement messages.

### Mass Assignment Protection

- `RegisterRequest` schema defines an explicit allowlist of fields (`full_name`, `email`, `password`).
- Pydantic v2 ignores extra fields by default — `role`, `organization_id`, `is_admin`, `permissions`, `is_superuser` are all silently ignored.
- No fields are passed through from the request to the `User` model beyond the explicit allowlist.

### Account Status

- New accounts are created with `is_active=True`, `is_verified=False`, `account_status=active`.
- Verification flow (email OTP, etc.) is deferred to a future phase.

## Consequences

### Positive

- Eliminates privilege escalation vector via public registration.
- Email normalization prevents duplicate accounts from case variations.
- Mass assignment protection ensures users cannot grant themselves elevated privileges.
- Password never leaked in API responses.
- All existing auth flows (login, refresh, /me, logout) remain backward compatible.
- 37+ new tests covering email normalization, mass assignment, and security guarantees.

### Negative

- Users must remember the exact case of their email (mitigated by normalization on both registration and login).
- Organization admin / HR / recruiter onboarding requires invitation flow (intentional — enterprise security).

### Neutral

- CandidateProfile is not auto-created on registration (deferred to profile completion flow).
- Email uniqueness constraint at DB level is case-sensitive in PostgreSQL — normalization at the application layer is the primary defense.

## References

- `backend/app/domain/schemas.py` — `RegisterRequest`, `LoginRequest`
- `backend/app/services/auth.py` — `AuthService.register()`, `AuthService.login()`
- `frontend/src/pages/Register.tsx` — Candidate-only UI
- `backend/tests/test_phase3_registration.py` — 37+ security tests
