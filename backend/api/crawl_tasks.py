import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

from auth.deps import get_current_user
from crawl.scheduler import compute_next_run, scheduler
from crawl.sources import get_source, list_sources
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import Collection, User
from models.crawl_task import CrawlTask
from models.crawl_task_run import CrawlTaskRun
from pydantic import BaseModel
from services.permission_service import check_collection_permission
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/crawl-tasks", tags=["crawl-tasks"])
logger = logging.getLogger(__name__)


# --- Pydantic schemas ---


class CrawlTaskCreate(BaseModel):
    name: str
    source_type: str
    source_config: dict
    schedule_type: Literal["once", "daily", "weekly", "monthly"] = "daily"
    time_range: str = "1d"
    target_mode: Literal["append", "create_new"] = "append"
    target_collection_id: str | None = None
    new_collection_prefix: str | None = None
    duplicate_strategy: Literal["skip", "update"] = "skip"


class CrawlTaskUpdate(BaseModel):
    name: str | None = None
    source_config: dict | None = None
    schedule_type: Literal["once", "daily", "weekly", "monthly"] | None = None
    time_range: str | None = None
    target_mode: Literal["append", "create_new"] | None = None
    target_collection_id: str | None = None
    new_collection_prefix: str | None = None
    duplicate_strategy: Literal["skip", "update"] | None = None


def _require_target_access(
    db: Session,
    user_id: str,
    target_mode: str,
    target_collection_id: str | None,
    new_collection_prefix: str | None,
) -> None:
    """Validate a task's complete target configuration and authorization."""
    if target_mode == "append":
        if not target_collection_id:
            raise HTTPException(
                status_code=400, detail="target_collection_id required for append mode"
            )
        collection = (
            db.query(Collection).filter(Collection.id == target_collection_id).first()
        )
        if not collection:
            raise HTTPException(status_code=404, detail="Target collection not found")
        if not check_collection_permission(db, user_id, collection.id, "edit"):
            raise HTTPException(
                status_code=403, detail="No permission to edit target collection"
            )
    elif not new_collection_prefix:
        raise HTTPException(
            status_code=400,
            detail="new_collection_prefix required for create_new mode",
        )


def _task_to_dict(task: CrawlTask) -> dict:
    return {
        "id": task.id,
        "name": task.name,
        "source_type": task.source_type,
        "source_config": task.source_config,
        "schedule_type": task.schedule_type,
        "time_range": task.time_range,
        "target_mode": task.target_mode,
        "target_collection_id": task.target_collection_id,
        "new_collection_prefix": task.new_collection_prefix,
        "duplicate_strategy": task.duplicate_strategy,
        "is_enabled": task.is_enabled,
        "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
        "last_run_status": task.last_run_status,
        "last_run_result": task.last_run_result,
        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


# --- Data source meta API ---


@router.get("/sources", tags=["crawl-sources"])
def get_crawl_sources():
    """List available data sources and their config schemas"""
    return [s.to_dict() for s in list_sources()]


# --- CRUD ---


@router.get("")
def list_crawl_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = (
        db.query(CrawlTask)
        .filter(CrawlTask.user_id == current_user.id)
        .order_by(CrawlTask.created_at.desc())
        .all()
    )
    return [_task_to_dict(t) for t in tasks]


@router.post("")
def create_crawl_task(
    body: CrawlTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate source type
    try:
        source = get_source(body.source_type)
        source.validate_config(body.source_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _require_target_access(
        db,
        current_user.id,
        body.target_mode,
        body.target_collection_id,
        body.new_collection_prefix,
    )

    now = datetime.now(timezone.utc)
    task = CrawlTask(
        user_id=current_user.id,
        name=body.name,
        source_type=body.source_type,
        source_config=body.source_config,
        schedule_type=body.schedule_type,
        time_range=body.time_range,
        target_mode=body.target_mode,
        target_collection_id=body.target_collection_id,
        new_collection_prefix=body.new_collection_prefix,
        duplicate_strategy=body.duplicate_strategy,
        is_enabled=True,
        next_run_at=now
        if body.schedule_type == "once"
        else compute_next_run(body.schedule_type, now),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.get("/{task_id}")
def get_crawl_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_dict(task)


@router.put("/{task_id}")
def update_crawl_task(
    task_id: str,
    body: CrawlTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = body.model_dump(exclude_none=True)

    # Validate source config if provided
    if "source_config" in update_data:
        try:
            source = get_source(task.source_type)
            source.validate_config(update_data["source_config"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    _require_target_access(
        db,
        current_user.id,
        update_data.get("target_mode", task.target_mode),
        update_data.get("target_collection_id", task.target_collection_id),
        update_data.get("new_collection_prefix", task.new_collection_prefix),
    )

    for key, value in update_data.items():
        setattr(task, key, value)

    # Recalculate next_run_at if schedule changed
    if "schedule_type" in update_data:
        now = datetime.now(timezone.utc)
        task.next_run_at = compute_next_run(task.schedule_type, now)

    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.delete("/{task_id}")
def delete_crawl_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}


# --- Task control ---


@router.post("/{task_id}/enable")
def enable_crawl_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _require_target_access(
        db,
        current_user.id,
        task.target_mode,
        task.target_collection_id,
        task.new_collection_prefix,
    )
    task.is_enabled = True
    now = datetime.now(timezone.utc)
    if task.schedule_type == "once":
        # Re-enabling a one-time task: schedule it to run now
        task.next_run_at = now
    elif not task.next_run_at or task.next_run_at.replace(tzinfo=None) < now.replace(
        tzinfo=None
    ):
        task.next_run_at = compute_next_run(task.schedule_type, now)
    db.commit()
    return _task_to_dict(task)


@router.post("/{task_id}/disable")
def disable_crawl_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_enabled = False
    db.commit()
    return _task_to_dict(task)


@router.post("/{task_id}/run-now")
async def run_crawl_task_now(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _require_target_access(
        db,
        current_user.id,
        task.target_mode,
        task.target_collection_id,
        task.new_collection_prefix,
    )

    # Reentrancy guard: reject duplicate trigger while task is running
    if scheduler.is_task_running(task_id):
        raise HTTPException(status_code=409, detail="Task is already running")

    # Run in background to not block the request
    asyncio.create_task(scheduler.run_task_now(task_id))
    return {"ok": True, "message": "Task execution started"}


# --- Run history ---


@router.get("/{task_id}/runs")
def list_task_runs(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(CrawlTask)
        .filter(CrawlTask.id == task_id, CrawlTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    runs = (
        db.query(CrawlTaskRun)
        .filter(CrawlTaskRun.task_id == task_id)
        .order_by(CrawlTaskRun.started_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "result": r.result,
            "collection_id": r.collection_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ]
