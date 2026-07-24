"""Add administrator provenance and align crawl task foreign keys.

Revision ID: 20260724_02
Revises: 20260724_01
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_02"
down_revision: str | None = "20260724_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _indexes(table_name: str) -> set[str]:
    return {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def upgrade() -> None:
    if "admin_source" not in _columns("users"):
        op.add_column("users", sa.Column("admin_source", sa.String(length=16)))
    # Existing database roles came either from the configured legacy admin or
    # OAuth group synchronization. App startup restores the configured account
    # to manual provenance after migration.
    op.execute(
        "UPDATE users SET admin_source = "
        "CASE WHEN oauth_provider IS NOT NULL AND password_hash IS NULL "
        "THEN 'oauth' ELSE 'manual' END "
        "WHERE is_admin = 1 AND admin_source IS NULL"
    )

    # Normalize legacy references before rebuilding the crawl tables with the
    # same actions declared by the ORM models.
    op.execute(
        "DELETE FROM crawl_task_runs WHERE task_id NOT IN (SELECT id FROM crawl_tasks)"
    )
    op.execute("DELETE FROM crawl_tasks WHERE user_id NOT IN (SELECT id FROM users)")
    op.execute(
        "UPDATE crawl_tasks SET target_collection_id = NULL, is_enabled = 0, "
        "last_run_status = 'failed', "
        'last_run_result = \'{"error":"target_collection_deleted"}\' '
        "WHERE target_collection_id IS NOT NULL "
        "AND target_collection_id NOT IN (SELECT id FROM collections)"
    )

    # SQLite keeps index names when a table is renamed, so release the names
    # before rebuilding them on the replacement tables.
    for table_name, index_names in (
        (
            "crawl_tasks",
            ("ix_crawl_tasks_user_id", "ix_crawl_tasks_next_run_at"),
        ),
        ("crawl_task_runs", ("ix_crawl_task_runs_task_id",)),
    ):
        existing_indexes = _indexes(table_name)
        for index_name in index_names:
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name=table_name)

    # Rebuild both parent and child together. Renaming only crawl_tasks on
    # SQLite can retarget the child FK to the temporary legacy table.
    op.rename_table("crawl_task_runs", "crawl_task_runs_legacy_20260724_02")
    op.rename_table("crawl_tasks", "crawl_tasks_legacy_20260724_02")

    op.create_table(
        "crawl_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_config", sa.JSON(), nullable=False),
        sa.Column("schedule_type", sa.String(), nullable=False),
        sa.Column("time_range", sa.String(), nullable=False),
        sa.Column("target_mode", sa.String(), nullable=False),
        sa.Column("target_collection_id", sa.String()),
        sa.Column("new_collection_prefix", sa.String()),
        sa.Column("duplicate_strategy", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime()),
        sa.Column("last_run_status", sa.String()),
        sa.Column("last_run_result", sa.JSON()),
        sa.Column("next_run_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["target_collection_id"], ["collections.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO crawl_tasks ("
        "id, user_id, name, source_type, source_config, schedule_type, time_range, "
        "target_mode, target_collection_id, new_collection_prefix, "
        "duplicate_strategy, is_enabled, last_run_at, last_run_status, "
        "last_run_result, next_run_at, created_at, updated_at"
        ") SELECT id, user_id, name, source_type, source_config, schedule_type, "
        "time_range, target_mode, target_collection_id, new_collection_prefix, "
        "duplicate_strategy, is_enabled, last_run_at, last_run_status, "
        "last_run_result, next_run_at, created_at, updated_at "
        "FROM crawl_tasks_legacy_20260724_02"
    )
    op.create_index("ix_crawl_tasks_user_id", "crawl_tasks", ["user_id"])
    op.create_index("ix_crawl_tasks_next_run_at", "crawl_tasks", ["next_run_at"])

    op.create_table(
        "crawl_task_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("collection_id", sa.String()),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["task_id"], ["crawl_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO crawl_task_runs ("
        "id, task_id, status, result, collection_id, started_at, finished_at"
        ") SELECT id, task_id, status, result, collection_id, started_at, "
        "finished_at FROM crawl_task_runs_legacy_20260724_02"
    )
    op.create_index("ix_crawl_task_runs_task_id", "crawl_task_runs", ["task_id"])

    op.drop_table("crawl_task_runs_legacy_20260724_02")
    op.drop_table("crawl_tasks_legacy_20260724_02")


def downgrade() -> None:
    raise RuntimeError(
        "This integrity migration is intentionally irreversible; restore the "
        "pre-migration database backup instead."
    )
