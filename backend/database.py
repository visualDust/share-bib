import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from config import config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Ensure data directory exists
data_dir = Path(config.data_dir)
data_dir.mkdir(parents=True, exist_ok=True)

db_path = data_dir / "paper_collector.db"
DATABASE_URL = f"sqlite:///{db_path.resolve()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import (  # noqa: F401
        Collection,
        CollectionPaper,
        CollectionPermission,
        CrawlTask,
        CrawlTaskRun,
        ImportTask,
        Paper,
        User,
        UserSetting,
    )

    Base.metadata.create_all(bind=engine)
    os.chmod(db_path, 0o600)
    _upgrade_schema()

    # Compatibility bridge for installations created before the database-backed
    # administrator role became authoritative. The configured account was the
    # legacy authority, so preserve it as manual even when it also has a linked
    # OAuth identity; all other legacy OAuth administrators can then follow
    # provider group membership safely.
    if config.admin_username:
        db = SessionLocal()
        try:
            has_admin = db.query(User).filter(User.is_admin.is_(True)).first()
            legacy_admin = (
                db.query(User).filter(User.username == config.admin_username).first()
            )
            if legacy_admin:
                changed = False
                if not has_admin:
                    legacy_admin.is_admin = True
                    changed = True
                if legacy_admin.is_admin and legacy_admin.admin_source != "manual":
                    legacy_admin.admin_source = "manual"
                    changed = True
                if changed:
                    db.commit()
        finally:
            db.close()


def _upgrade_schema() -> None:
    """Apply versioned migrations, backing up populated SQLite databases."""
    alembic_config = Config(str(Path(__file__).with_name("alembic.ini")))
    script = ScriptDirectory.from_config(alembic_config)
    expected_heads = set(script.get_heads())
    with engine.connect() as connection:
        current_heads = set(MigrationContext.configure(connection).get_current_heads())
        has_data = connection.exec_driver_sql("SELECT COUNT(*) FROM users").scalar() > 0

    if current_heads == expected_heads:
        return

    if has_data:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_name(f"{db_path.name}.bak-pre-migration-{timestamp}")
        source = sqlite3.connect(db_path)
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        os.chmod(backup_path, 0o600)

    command.upgrade(alembic_config, "head")
