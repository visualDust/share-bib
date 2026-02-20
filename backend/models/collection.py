from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    visibility: Mapped[str] = mapped_column(String, default="private", index=True)
    allow_export: Mapped[bool] = mapped_column(Boolean, default=False)
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    task_source: Mapped[str | None] = mapped_column(String)
    task_source_display: Mapped[str | None] = mapped_column(String)
    task_config: Mapped[dict | None] = mapped_column(JSON)
    tags: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator: Mapped["User"] = relationship(back_populates="collections")  # noqa: F821
    permissions: Mapped[list["CollectionPermission"]] = relationship(  # noqa: F821
        back_populates="collection", cascade="all, delete-orphan"
    )
    papers: Mapped[list["CollectionPaper"]] = relationship(  # noqa: F821
        back_populates="collection", cascade="all, delete-orphan"
    )
