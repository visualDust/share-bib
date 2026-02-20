import asyncio
import logging
from datetime import datetime, timezone, timedelta

from database import SessionLocal
from models.crawl_task import CrawlTask
from models.crawl_task_run import CrawlTaskRun
from crawl.executor import CrawlExecutor

logger = logging.getLogger(__name__)


def compute_next_run(schedule_type: str, from_time: datetime) -> datetime | None:
    """计算下次运行时间。once 类型返回 None 表示不再调度。"""
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
    """轻量级爬取调度器，随 FastAPI 生命周期启停"""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._executor = CrawlExecutor()

    async def start(self):
        """FastAPI startup 时调用"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("CrawlScheduler started")

    async def stop(self):
        """FastAPI shutdown 时调用"""
        self._stop_event.set()
        if self._task:
            await self._task
        logger.info("CrawlScheduler stopped")

    async def run_task_now(self, task_id: str):
        """立即执行一个任务（不影响调度）"""
        db = SessionLocal()
        try:
            task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
            if not task:
                return
            await self._execute_task(task, db)
        finally:
            db.close()

    async def _run_loop(self):
        """每 60 秒检查一次是否有任务需要执行"""
        while not self._stop_event.is_set():
            try:
                await self._check_and_run()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            # 等待 60 秒或被停止
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
                break
            except asyncio.TimeoutError:
                pass

    async def _check_and_run(self):
        """检查所有到期任务并串行执行"""
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
        """执行单个爬取任务"""
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
