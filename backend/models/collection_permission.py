from datetime import datetime, timezone

from database import Base
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CollectionPermission(Base):
    __tablename__ = "collection_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission: Mapped[str] = mapped_column(String, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint(
            "permission IN ('view', 'edit')", name="ck_collection_permission_role"
        ),
        UniqueConstraint(
            "collection_id", "user_id", name="uq_collection_permission_user"
        ),
    )

    collection: Mapped["Collection"] = relationship(back_populates="permissions")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="permissions")  # noqa: F821
