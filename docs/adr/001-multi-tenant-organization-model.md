# ADR-001: Multi-Tenant Organization Model

## Status

Accepted

## Date

2026-08-20

## Context

The platform needs to support multiple organizations (tenants) so that different companies can independently manage their hiring workflows, candidates, and recruiters without cross-tenant data leakage. Prior to this change, all users existed in a flat role hierarchy with no organizational boundary.

## Decision

Introduce Organization, OrganizationMembership, and Invitation as first-class domain entities.

### Organization Model

- **UUID primary key** — consistent with all other domain models, safe for distributed systems.
- **Unique slug** — lowercase alphanumeric + hyphens (`^[a-z0-9][a-z0-9\-]*$`), used in URLs and as the stable external identifier.
- **Status field** — `active`, `inactive`, `suspended`, `deactivated` for lifecycle management.
- **Nullable profile fields** — `description`, `official_email`, `domain`, `logo_url` added for future profile pages without blocking Phase 2.

### Membership Model

- Composite uniqueness constraint on `(user_id, organization_id)` prevents duplicate memberships.
- Roles scoped to organization: `organization_admin`, `hr_manager`, `recruiter`. The `candidate` role is global and not membership-scoped.
- Status field tracks membership lifecycle: `invited`, `pending`, `active`, `suspended`, `revoked`.
- `joined_at` and `invited_by_id` provide audit trail.

### Invitation Model

- Token-based invitations with expiry (7 days), scoped to an organization and a specific role.
- Status lifecycle: `pending` → `accepted` | `expired` | `revoked`.
- Accepting an invitation creates the user (if not existing) and the membership in one transaction.

### Tenant Ownership

After analysis, only `jobs` and `audit_logs` received an `organization_id` foreign key. Other resources (candidates, resumes, applications) remain user-owned and will be scoped to organizations through job relationships in later phases.

### Role Hierarchy

The role hierarchy is:

```
super_admin > organization_admin > hr_manager > recruiter > candidate
```

- `super_admin` — platform-wide, not tied to any organization.
- `organization_admin` — manages one organization, can invite members.
- `hr_manager` — can manage members and view org data.
- `recruiter` — can manage jobs and view org data.
- `candidate` — global role, registers via public endpoint, not membership-scoped.

Public registration is restricted to `candidate` only. All privileged roles require invitation from an organization admin.

### Legacy Role Mapping

Legacy role names (`admin`, `hr`) are mapped to new names via `LEGACY_ROLE_MAP` for backward compatibility. Existing users retain their `user_roles` entries.

## Consequences

### Positive

- Cross-organization data isolation enforced at the API layer via `RequireOrgMembership` dependency.
- Organizations can independently manage their teams without platform admin intervention.
- Slug-based URLs enable clean frontend routing (`/org/{slug}/team`).
- Invitation flow provides secure, auditable onboarding of privileged users.
- Migration 0012 is idempotent and SQLite-compatible for local development.

### Negative

- Additional database tables and queries (mitigated by proper indexing).
- Invitation flow adds complexity to user onboarding (acceptable for enterprise use case).
- Slug uniqueness requires coordination across tenants (mitigated by UUID primary key as the true identifier).

### Neutral

- Demo organizations (`acme-corp`, `globex-industries`) are seeded on startup for development.
- Existing users are auto-migrated into Acme Corporation with appropriate membership roles.
