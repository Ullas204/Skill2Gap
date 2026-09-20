"""Phase 4 - Invitation query indexes (status, expires_at)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-23

Adds non-clustered lookup indexes used by invitation lifecycle queries
(listing by org + status, expiry sweeps). Safe and fully reversible.
Idempotent: skips indexes that already exist.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_TABLE = "invitations"
_INDEXES = (
    ("ix_invitations_status", "status"),
    ("ix_invitations_expires_at", "expires_at"),
)


def _existing_indexes(bind) -> set:
    insp = inspect(bind)
    return {ix["name"] for ix in insp.get_indexes(_TABLE)}


def upgrade() -> None:
    existing = _existing_indexes(op.get_bind())
    for name, column in _INDEXES:
        if name not in existing:
            op.create_index(name, _TABLE, [column])


def downgrade() -> None:
    existing = _existing_indexes(op.get_bind())
    for name, _column in _INDEXES:
        if name in existing:
            op.drop_index(name, table_name=_TABLE)
