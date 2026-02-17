from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CollectionPaper(Base):
    __tablename__ = "collection_papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paper_id: Mapped[str] = mapped_column(
        String, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_name: Mapped[str | None] = mapped_column(String)
    group_tag: Mapped[str | None] = mapped_column(String)
    section_name: Mapped[str | None] = mapped_column(String)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("collection_id", "paper_id"),)

    collection: Mapped["Collection"] = relationship(back_populates="papers")  # noqa: F821
    paper: Mapped["Paper"] = relationship(back_populates="collections")  # noqa: F821
