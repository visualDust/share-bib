from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import config

# Ensure data directory exists
data_dir = Path(config.data_dir)
data_dir.mkdir(parents=True, exist_ok=True)

db_path = data_dir / "paper_collector.db"
DATABASE_URL = f"sqlite:///{db_path.resolve()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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
        User,
        Collection,
        Paper,
        CollectionPaper,
        CollectionPermission,
        ImportTask,
    )

    Base.metadata.create_all(bind=engine)
