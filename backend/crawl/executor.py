import logging
import uuid
from copy import deepcopy
from datetime import datetime, timezone

from models import Collection, CollectionPaper, Paper, User
from models.crawl_task import CrawlTask
from models.user_setting import UserSetting
from services.collection_ids import slugify_collection_name
from services.deduplication import find_duplicate_paper
from services.paper_service import update_paper_for_collection
from services.permission_service import check_collection_permission
from sqlalchemy import func
from sqlalchemy.orm import Session

from crawl.sources import get_source

logger = logging.getLogger(__name__)


class CrawlExecutor:
    """Orchestrate crawl execution: source -> dedup -> write to collection"""

    async def execute(self, task: CrawlTask, db: Session) -> dict:
        """
        Execute a crawl task and return a result summary.
        """
        task_id = task.id
        source = get_source(task.source_type)
        execution_config = self._execution_config(task)
        result = {
            "new_papers": 0,
            "skipped": 0,
            "updated": 0,
            "errors": [],
            "collection_id": None,
        }

        task_owner = db.query(User).filter(User.id == task.user_id).first()
        if not task_owner or not task_owner.is_active:
            task.is_enabled = False
            return {
                **result,
                "error": "task_owner_inactive",
                "message": "The crawl task owner no longer exists or is inactive",
            }

        try:
            # 1. Validate an existing append target. New collections are
            # created only after the network wait so no write transaction is
            # held while waiting on a remote source.
            collection = None
            if task.target_mode == "append":
                collection = self._resolve_collection(task, db)
                if collection is None:
                    target_error = task.last_run_result or {
                        "error": "target_collection_deleted",
                        "message": (
                            f"Collection '{task.target_collection_id}' no longer exists"
                        ),
                    }
                    return {**result, **target_error}

            # 2. Load user settings (e.g. API key)
            user_settings = self._load_user_settings(task.user_id, db)
            source_config = dict(task.source_config or {})
            last_run_at = task.last_run_at

            # End the read transaction before awaiting remote I/O. Permission
            # revocations and task changes can now commit independently.
            db.rollback()

            # 3. Execute crawl
            papers = await source.fetch(source_config, last_run_at, user_settings)

            # Reload the task and target in a new transaction after the wait.
            task = (
                db.query(CrawlTask)
                .populate_existing()
                .filter(CrawlTask.id == task_id)
                .first()
            )
            if not task:
                return {
                    **result,
                    "error": "task_deleted",
                    "message": "The crawl task was deleted while it was running",
                }
            if not task.is_enabled:
                return {
                    **result,
                    "error": "task_disabled",
                    "message": "The crawl task was disabled while it was running",
                }
            if self._execution_config(task) != execution_config:
                return {
                    **result,
                    "error": "task_changed_during_execution",
                    "message": (
                        "The crawl task configuration changed while it was running; "
                        "fetched results were not saved"
                    ),
                }
            collection = self._resolve_collection(task, db)
            if collection is None:
                target_error = task.last_run_result or {
                    "error": "target_collection_deleted",
                    "message": (
                        f"Collection '{task.target_collection_id}' no longer exists"
                    ),
                }
                return {**result, **target_error}
            result["collection_id"] = collection.id

            authorization_error = self._authorization_error(task, collection, db)
            if authorization_error:
                db.rollback()
                return {**result, **authorization_error}

            # 4. Get current max display_order
            max_order = (
                db.query(func.max(CollectionPaper.display_order))
                .filter(CollectionPaper.collection_id == collection.id)
                .scalar()
                or 0
            )

            # 5. Deduplicate and write each paper
            for fetched in papers:
                savepoint = db.begin_nested()
                new_delta = 0
                skipped_delta = 0
                updated_delta = 0
                try:
                    paper_dict = fetched.to_paper_dict()
                    existing, _ = find_duplicate_paper(
                        db,
                        paper_dict,
                        collection_id=(
                            collection.id if task.target_mode == "append" else None
                        ),
                        owner_user_id=(
                            task.user_id if task.target_mode != "append" else None
                        ),
                    )

                    if existing:
                        if task.duplicate_strategy == "update":
                            paper = update_paper_for_collection(
                                db,
                                existing,
                                collection.id,
                                {
                                    key: value
                                    for key, value in paper_dict.items()
                                    if value is not None and key != "status"
                                },
                            )
                            updated_delta = 1
                        else:  # skip
                            paper = existing
                            skipped_delta = 1
                    else:
                        paper = Paper(**paper_dict)
                        db.add(paper)
                        db.flush()
                        new_delta = 1

                    # Deduplicate within collection
                    cp_exists = (
                        db.query(CollectionPaper)
                        .filter(
                            CollectionPaper.collection_id == collection.id,
                            CollectionPaper.paper_id == paper.id,
                        )
                        .first()
                    )
                    if not cp_exists:
                        max_order += 1
                        cp = CollectionPaper(
                            collection_id=collection.id,
                            paper_id=paper.id,
                            group_name="Crawled",
                            group_tag="crawled",
                            section_name="All Papers",
                            display_order=max_order,
                        )
                        db.add(cp)

                    db.flush()
                    savepoint.commit()
                    result["new_papers"] += new_delta
                    result["skipped"] += skipped_delta
                    result["updated"] += updated_delta

                except Exception as e:
                    if savepoint.is_active:
                        savepoint.rollback()
                    logger.error(f"Error processing paper '{fetched.title}': {e}")
                    result["errors"].append({"title": fetched.title, "reason": str(e)})

            authorization_error = self._authorization_error(task, collection, db)
            if authorization_error:
                db.rollback()
                return {
                    **result,
                    "new_papers": 0,
                    "updated": 0,
                    **authorization_error,
                }

        except Exception as e:
            logger.error(f"Crawl execution failed for task {task_id}: {e}")
            db.rollback()
            return {
                **result,
                "new_papers": 0,
                "updated": 0,
                "error": "crawl_execution_failed",
                "message": str(e),
            }

        return result

    @staticmethod
    def _execution_config(task: CrawlTask) -> dict:
        """Snapshot every task field that affects fetch or persistence."""
        return {
            "user_id": task.user_id,
            "name": task.name,
            "source_type": task.source_type,
            "source_config": deepcopy(task.source_config or {}),
            "time_range": task.time_range,
            "target_mode": task.target_mode,
            "target_collection_id": task.target_collection_id,
            "new_collection_prefix": task.new_collection_prefix,
            "duplicate_strategy": task.duplicate_strategy,
        }

    def _authorization_error(
        self, task: CrawlTask, collection: Collection, db: Session
    ) -> dict | None:
        """Recheck principals after network waits and before persistence."""
        active_owner = (
            db.query(User.id)
            .filter(User.id == task.user_id, User.is_active.is_(True))
            .first()
        )
        if not active_owner:
            return {
                "error": "task_owner_inactive",
                "message": "The crawl task owner no longer exists or is inactive",
            }
        if task.target_mode == "append" and not check_collection_permission(
            db, task.user_id, collection.id, "edit"
        ):
            return {
                "error": "target_permission_revoked",
                "message": "The task owner can no longer edit the target collection",
            }
        return None

    def _load_user_settings(self, user_id: str, db: Session) -> dict:
        """Load user settings as a {key: value} dict"""
        rows = db.query(UserSetting).filter(UserSetting.user_id == user_id).all()
        return {r.key: r.value for r in rows}

    def _resolve_collection(self, task: CrawlTask, db: Session) -> Collection | None:
        """Resolve or create the target collection."""
        if task.target_mode == "append":
            collection = (
                db.query(Collection)
                .filter(Collection.id == task.target_collection_id)
                .first()
            )
            if not collection:
                # Collection has been deleted, disable the task
                task.is_enabled = False
                task.last_run_status = "failed"
                task.last_run_result = {
                    "error": "target_collection_deleted",
                    "message": f"Collection '{task.target_collection_id}' no longer exists",
                }
                return None
            if not check_collection_permission(db, task.user_id, collection.id, "edit"):
                task.is_enabled = False
                task.last_run_status = "failed"
                task.last_run_result = {
                    "error": "target_permission_revoked",
                    "message": "The task owner can no longer edit the target collection",
                }
                return None
            return collection
        else:
            # create_new mode: create a new collection each time
            prefix = task.new_collection_prefix or task.name
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            title = f"{prefix} - {date_str}"
            slug = slugify_collection_name(prefix, max_length=40)
            cid = f"{slug}-{date_str}"

            # Ensure unique
            if db.query(Collection).filter(Collection.id == cid).first():
                cid = f"{cid}-{uuid.uuid4().hex[:4]}"

            collection = Collection(
                id=cid,
                title=title,
                description=f"Auto-created by crawl task: {task.name}",
                created_by=task.user_id,
                visibility="private",
                task_type="crawl_task",
                task_source=task.source_type,
                task_source_display=task.name,
            )
            db.add(collection)
            return collection
