"""Harden authorization and relational integrity.

Revision ID: 20260724_01
Revises:
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    # Preserve task history while removing only references whose parent row is
    # already gone. Unreferenced papers are intentionally retained.
    op.execute(
        "DELETE FROM collection_papers "
        "WHERE collection_id NOT IN (SELECT id FROM collections) "
        "OR paper_id NOT IN (SELECT id FROM papers)"
    )
    op.execute(
        "DELETE FROM collection_permissions "
        "WHERE collection_id NOT IN (SELECT id FROM collections) "
        "OR user_id NOT IN (SELECT id FROM users)"
    )
    op.execute(
        "UPDATE import_tasks SET collection_id = NULL "
        "WHERE collection_id IS NOT NULL "
        "AND collection_id NOT IN (SELECT id FROM collections)"
    )
    op.execute("DELETE FROM import_tasks WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute(
        "DELETE FROM crawl_task_runs WHERE task_id NOT IN (SELECT id FROM crawl_tasks)"
    )
    op.execute(
        "UPDATE crawl_tasks SET is_enabled = 0, target_collection_id = NULL, "
        "last_run_status = 'failed', "
        'last_run_result = \'{"error":"target_collection_deleted"}\' '
        "WHERE target_collection_id IS NOT NULL "
        "AND target_collection_id NOT IN (SELECT id FROM collections)"
    )
    op.execute("DELETE FROM api_keys WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute("DELETE FROM user_settings WHERE user_id NOT IN (SELECT id FROM users)")

    if "token_version" not in _columns("users"):
        op.add_column(
            "users",
            sa.Column(
                "token_version", sa.Integer(), nullable=False, server_default="0"
            ),
        )

    # A user has exactly one effective role per collection. When legacy rows
    # contain both roles, retain edit (the stronger role).
    op.rename_table("collection_permissions", "collection_permissions_legacy")
    op.create_table(
        "collection_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("collection_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("permission", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "permission IN ('view', 'edit')", name="ck_collection_permission_role"
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collection_id", "user_id", name="uq_collection_permission_user"
        ),
    )
    op.execute(
        "INSERT INTO collection_permissions "
        "(collection_id, user_id, permission, granted_at) "
        "SELECT collection_id, user_id, "
        "CASE WHEN MAX(CASE WHEN permission = 'edit' THEN 1 ELSE 0 END) = 1 "
        "THEN 'edit' ELSE 'view' END, MIN(granted_at) "
        "FROM collection_permissions_legacy "
        "WHERE permission IN ('view', 'edit') "
        "GROUP BY collection_id, user_id"
    )
    op.drop_table("collection_permissions_legacy")
    op.create_index(
        "ix_collection_permissions_collection_id",
        "collection_permissions",
        ["collection_id"],
    )
    op.create_index(
        "ix_collection_permissions_user_id",
        "collection_permissions",
        ["user_id"],
    )

    # Preserve import history when its collection is removed, while cascading
    # only when the owning user is intentionally deleted.
    op.rename_table("import_tasks", "import_tasks_legacy")
    op.create_table(
        "import_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("config", sa.JSON()),
        sa.Column("result", sa.JSON()),
        sa.Column("collection_id", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO import_tasks SELECT id, user_id, task_type, status, config, "
        "result, collection_id, created_at, completed_at FROM import_tasks_legacy"
    )
    op.drop_table("import_tasks_legacy")
    op.create_index("ix_import_tasks_status", "import_tasks", ["status"])
    op.create_index("ix_import_tasks_user_id", "import_tasks", ["user_id"])

    # These legacy tables had user_id columns but no database-level FK.
    op.rename_table("api_keys", "api_keys_legacy")
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO api_keys SELECT id, user_id, name, key_hash, key_prefix, "
        "is_active, last_used_at, created_at, updated_at FROM api_keys_legacy"
    )
    op.drop_table("api_keys_legacy")
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    op.rename_table("user_settings", "user_settings_legacy")
    op.create_table(
        "user_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", name="uq_user_settings_user_key"),
    )
    op.execute(
        'INSERT INTO user_settings SELECT id, user_id, "key", value, '
        "created_at, updated_at FROM user_settings_legacy"
    )
    op.drop_table("user_settings_legacy")
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"])

    # Legacy installs may contain duplicate provider identities. Preserve every
    # account and its data, but detach the identity from all except the oldest
    # account before adding the uniqueness guarantee.
    op.execute(
        "UPDATE users SET oauth_provider = NULL, oauth_sub = NULL "
        "WHERE id IN ("
        "SELECT id FROM ("
        "SELECT id, ROW_NUMBER() OVER ("
        "PARTITION BY oauth_provider, oauth_sub "
        "ORDER BY created_at ASC, id ASC"
        ") AS identity_rank FROM users "
        "WHERE oauth_provider IS NOT NULL AND oauth_sub IS NOT NULL"
        ") ranked WHERE identity_rank > 1"
        ")"
    )

    op.create_index(
        "uq_user_oauth_identity",
        "users",
        ["oauth_provider", "oauth_sub"],
        unique=True,
        sqlite_where=sa.text("oauth_provider IS NOT NULL AND oauth_sub IS NOT NULL"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "This integrity migration is intentionally irreversible; restore the "
        "pre-migration database backup instead."
    )
