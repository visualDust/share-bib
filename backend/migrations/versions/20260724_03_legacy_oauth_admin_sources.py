"""Classify legacy OAuth-derived administrator roles.

Revision ID: 20260724_03
Revises: 20260724_02
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260724_03"
down_revision: str | None = "20260724_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Before admin_source existed, the only non-configured way to acquire the
    # database is_admin flag on an OAuth-only account was OAuth group
    # synchronization. Password-backed admins remain manual, and app startup
    # also restores the configured legacy administrator to manual provenance.
    op.execute(
        "UPDATE users SET admin_source = 'oauth' "
        "WHERE is_admin = 1 AND oauth_provider IS NOT NULL "
        "AND password_hash IS NULL"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET admin_source = 'manual' "
        "WHERE is_admin = 1 AND admin_source = 'oauth'"
    )
