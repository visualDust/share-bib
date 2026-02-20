import asyncio
import logging
from datetime import datetime, timezone, timedelta

from database import SessionLocal
from models.crawl_task import CrawlTask
from models.crawl_task_run import CrawlTaskRun
from crawl.executor import CrawlExecutor

logger = logging.getLogger(__name__)


def compute_next_run(schedule_type: str, from_time: datetime) -> datetime | None:
    """Compute next run time. Returns None for 'once' type (no further scheduling)."""
    if schedule_type == "once":
        return None
    elif schedule_type == "daily":
        return from_time + timedelta(days=1)
    elif schedule_type == "weekly":
        return from_time + timedelta(weeks=1)
    elif schedule_type == "monthly":
        return from_time + timedelta(days=30)
    return from_time + timedelta(days=1)


class CrawlScheduler:
    """Lightweight crawl scheduler, starts and stops with FastAPI lifecycle"""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._executor = CrawlExecutor()
        self._running_tasks: set[str] = (
            set()
        )  # Reentrancy guard: currently executing task IDs

    async def start(self):
        """Called on FastAPI startup"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("CrawlScheduler started")

    async def stop(self):
        """Called on FastAPI shutdown"""
        self._stop_event.set()
        if self._task:
            await self._task
        logger.info("CrawlScheduler stopped")

    async def run_task_now(self, task_id: str) -> bool:
        """Run a task immediately. Returns False if the task is already running."""
        if task_id in self._running_tasks:
            logger.warning(f"Task {task_id} is already running, skipping")
            return False
        db = SessionLocal()
        try:
            task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
            if not task:
                return False
            await self._execute_task(task, db)
            return True
        finally:
            db.close()

    async def _run_loop(self):
        """Check for due tasks every 60 seconds"""
        while not self._stop_event.is_set():
            try:
                await self._check_and_run()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            # Wait 60 seconds or until stopped
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                break
            except asyncio.TimeoutError:
                pass

    async def _check_and_run(self):
        """Check all due tasks and execute them serially"""
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            due_tasks = (
                db.query(CrawlTask)
                .filter(
                    CrawlTask.is_enabled == True,  # noqa: E712
                    CrawlTask.next_run_at <= now,
                )
                .all()
            )

            for task in due_tasks:
                await self._execute_task(task, db)
        finally:
            db.close()

    async def _execute_task(self, task: CrawlTask, db):
        """Execute a single crawl task"""
        if task.id in self._running_tasks:
            logger.warning(f"Task {task.name} ({task.id}) already running, skipping")
            return
        self._running_tasks.add(task.id)
        try:
            await self._execute_task_inner(task, db)
        finally:
            self._running_tasks.discard(task.id)

    def is_task_running(self, task_id: str) -> bool:
        return task_id in self._running_tasks

    async def _execute_task_inner(self, task: CrawlTask, db):
        """Execute a single crawl task (internal implementation)"""
        logger.info(f"Executing crawl task: {task.name} ({task.id})")
        now = datetime.now(timezone.utc)
        run = CrawlTaskRun(task_id=task.id, status="running", started_at=now)
        db.add(run)
        db.flush()

        try:
            result = await self._executor.execute(task, db)

            if result.get("error") == "target_collection_deleted":
                run.status = "failed"
                run.result = result
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
                return

            task.last_run_at = now
            task.last_run_status = "success"
            task.last_run_result = result
            task.next_run_at = compute_next_run(task.schedule_type, now)

            if result.get("errors"):
                task.last_run_status = "partial"

            # One-time tasks: disable after execution
            if task.schedule_type == "once":
                task.is_enabled = False

            run.status = task.last_run_status
            run.result = result
            run.collection_id = result.get("collection_id")
            run.finished_at = datetime.now(timezone.utc)

            db.commit()
            logger.info(
                f"Crawl task {task.name} completed: "
                f"{result.get('new_papers', 0)} new, "
                f"{result.get('skipped', 0)} skipped, "
                f"{result.get('updated', 0)} updated"
            )

        except Exception as e:
            logger.error(f"Crawl task {task.name} failed: {e}")
            task.last_run_at = now
            task.last_run_status = "failed"
            task.last_run_result = {"error": str(e)}
            task.next_run_at = compute_next_run(task.schedule_type, now)
            if task.schedule_type == "once":
                task.is_enabled = False

            run.status = "failed"
            run.result = {"error": str(e)}
            run.finished_at = datetime.now(timezone.utc)
            db.commit()


# Singleton instance
scheduler = CrawlScheduler()
