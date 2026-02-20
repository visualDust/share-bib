import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CrawlTask(Base):
    __tablename__ = "crawl_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    # 数据源配置
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # 调度配置
    schedule_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # daily/weekly/monthly
    time_range: Mapped[str] = mapped_column(String, default="1d")  # 1d/7d/30d

    # Collection 关联
    target_mode: Mapped[str] = mapped_column(
        String, nullable=False
    )  # append/create_new
    target_collection_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("collections.id", ondelete="SET NULL")
    )
    new_collection_prefix: Mapped[str | None] = mapped_column(String)

    # 去重策略
    duplicate_strategy: Mapped[str] = mapped_column(String, default="skip")

    # 状态
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_run_status: Mapped[str | None] = mapped_column(String)
    last_run_result: Mapped[dict | None] = mapped_column(JSON)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
