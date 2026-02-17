import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    authors: Mapped[list | None] = mapped_column(JSON)
    venue: Mapped[str | None] = mapped_column(String)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    abstract: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="no_access")
    bibtex_key: Mapped[str | None] = mapped_column(String, index=True)
    arxiv_id: Mapped[str | None] = mapped_column(String, index=True)
    doi: Mapped[str | None] = mapped_column(String, index=True)
    url_arxiv: Mapped[str | None] = mapped_column(String)
    url_pdf: Mapped[str | None] = mapped_column(String)
    url_code: Mapped[str | None] = mapped_column(String)
    url_project: Mapped[str | None] = mapped_column(String)
    tags: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    collections: Mapped[list["CollectionPaper"]] = relationship(back_populates="paper")  # noqa: F821
