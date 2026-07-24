from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event

import models  # noqa: F401
from database import Base


def _legacy_database(url: str):
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE users (
                id VARCHAR NOT NULL PRIMARY KEY,
                username VARCHAR NOT NULL UNIQUE,
                email VARCHAR UNIQUE,
                display_name VARCHAR,
                password_hash VARCHAR,
                oauth_provider VARCHAR,
                oauth_sub VARCHAR,
                is_admin BOOLEAN NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE crawl_tasks (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                name VARCHAR NOT NULL,
                source_type VARCHAR NOT NULL,
                source_config JSON NOT NULL,
                schedule_type VARCHAR NOT NULL,
                time_range VARCHAR NOT NULL,
                target_mode VARCHAR NOT NULL,
                target_collection_id VARCHAR REFERENCES collections(id),
                new_collection_prefix VARCHAR,
                duplicate_strategy VARCHAR NOT NULL,
                is_enabled BOOLEAN NOT NULL,
                last_run_at DATETIME,
                last_run_status VARCHAR,
                last_run_result JSON,
                next_run_at DATETIME,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_crawl_tasks_user_id ON crawl_tasks (user_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_crawl_tasks_next_run_at ON crawl_tasks (next_run_at)"
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE crawl_task_runs (
                id VARCHAR NOT NULL PRIMARY KEY,
                task_id VARCHAR NOT NULL REFERENCES crawl_tasks(id) ON DELETE CASCADE,
                status VARCHAR NOT NULL,
                result JSON,
                collection_id VARCHAR,
                started_at DATETIME NOT NULL,
                finished_at DATETIME
            )
            """
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_crawl_task_runs_task_id ON crawl_task_runs (task_id)"
        )
    Base.metadata.create_all(engine)
    return engine


def test_legacy_migration_normalizes_oauth_and_crawl_foreign_keys(tmp_path):
    database_path = tmp_path / "legacy.db"
    url = f"sqlite:///{database_path}"
    engine = _legacy_database(url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO users (
                id, username, email, display_name, password_hash,
                oauth_provider, oauth_sub, is_admin, is_active,
                created_at, updated_at
            ) VALUES
            ('oldest', 'oldest', 'oldest@example.com', NULL, NULL,
             'oidc', 'duplicate-sub', 1, 1,
             '2026-01-01 00:00:00', '2026-01-01 00:00:00'),
            ('newer', 'newer', 'newer@example.com', NULL, NULL,
             'oidc', 'duplicate-sub', 0, 1,
             '2026-01-02 00:00:00', '2026-01-02 00:00:00'),
            ('password-admin', 'password-admin', 'admin@example.com', NULL,
             'password-hash', 'oidc', 'manual-sub', 1, 1,
             '2026-01-03 00:00:00', '2026-01-03 00:00:00')
            """
        )
    engine.dispose()

    # Resolve against the backend's actual Alembic configuration rather than
    # relying on the pytest temporary directory layout.
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert context.get_current_revision() == "20260724_03"
        identities = connection.exec_driver_sql(
            "SELECT id, oauth_provider, oauth_sub, admin_source FROM users ORDER BY id"
        ).all()
        assert identities == [
            ("newer", None, None, None),
            ("oldest", "oidc", "duplicate-sub", "oauth"),
            ("password-admin", "oidc", "manual-sub", "manual"),
        ]
        task_fks = (
            connection.exec_driver_sql("PRAGMA foreign_key_list(crawl_tasks)")
            .mappings()
            .all()
        )
        assert any(
            row["table"] == "users" and row["on_delete"] == "CASCADE"
            for row in task_fks
        )
        assert any(
            row["table"] == "collections" and row["on_delete"] == "SET NULL"
            for row in task_fks
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []

    engine.dispose()

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO crawl_tasks (
                id, user_id, name, source_type, source_config, schedule_type,
                time_range, target_mode, duplicate_strategy, is_enabled,
                created_at, updated_at
            ) VALUES (
                'cascade-task', 'newer', 'Cascade', 'arxiv_rss', '{}', 'daily',
                '1d', 'create_new', 'skip', 1,
                '2026-01-03 00:00:00', '2026-01-03 00:00:00'
            )
            """
        )
        connection.exec_driver_sql(
            "INSERT INTO crawl_task_runs "
            "(id, task_id, status, started_at) VALUES "
            "('cascade-run', 'cascade-task', 'running', '2026-01-03 00:00:00')"
        )
        connection.exec_driver_sql("DELETE FROM users WHERE id = 'newer'")
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM crawl_tasks WHERE id = 'cascade-task'"
            ).scalar()
            == 0
        )
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM crawl_task_runs WHERE id = 'cascade-run'"
            ).scalar()
            == 0
        )
    engine.dispose()
