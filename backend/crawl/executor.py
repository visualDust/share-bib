import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Paper, Collection, CollectionPaper
from models.crawl_task import CrawlTask
from crawl.sources import get_source
from services.deduplication import find_duplicate_paper

logger = logging.getLogger(__name__)


class CrawlExecutor:
    """编排爬取执行：源 → 去重 → 写入 collection"""

    async def execute(self, task: CrawlTask, db: Session) -> dict:
        """
        执行一个爬取任务，返回结果摘要。
        """
        source = get_source(task.source_type)
        result = {
            "new_papers": 0,
            "skipped": 0,
            "updated": 0,
            "errors": [],
            "collection_id": None,
        }

        try:
            # 1. 获取或创建目标 collection
            collection = self._resolve_collection(task, db)
            if collection is None:
                return {
                    **result,
                    "error": "target_collection_deleted",
                    "message": f"Collection '{task.target_collection_id}' no longer exists",
                }
            result["collection_id"] = collection.id

            # 2. 执行爬取
            papers = await source.fetch(task.source_config, task.last_run_at)

            # 3. 获取当前最大 display_order
            max_order = (
                db.query(func.max(CollectionPaper.display_order))
                .filter(CollectionPaper.collection_id == collection.id)
                .scalar()
                or 0
            )

            # 4. 逐条去重并写入
            for fetched in papers:
                try:
                    paper_dict = fetched.to_paper_dict()
                    existing, _ = find_duplicate_paper(
                        db, paper_dict, owner_user_id=task.user_id
                    )

                    if existing:
                        if task.duplicate_strategy == "update":
                            for key, value in paper_dict.items():
                                if value is not None and key != "status":
                                    setattr(existing, key, value)
                            result["updated"] += 1
                            paper = existing
                        else:  # skip
                            paper = existing
                            result["skipped"] += 1
                    else:
                        paper = Paper(**paper_dict)
                        db.add(paper)
                        db.flush()
                        result["new_papers"] += 1

                    # Collection 内去重
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

                except Exception as e:
                    logger.error(f"Error processing paper '{fetched.title}': {e}")
                    result["errors"].append({"title": fetched.title, "reason": str(e)})

            db.commit()

        except Exception as e:
            logger.error(f"Crawl execution failed for task {task.id}: {e}")
            result["errors"].append({"reason": str(e)})

        return result

    def _resolve_collection(self, task: CrawlTask, db: Session) -> Collection | None:
        """获取或创建目标 collection。"""
        if task.target_mode == "append":
            collection = (
                db.query(Collection)
                .filter(Collection.id == task.target_collection_id)
                .first()
            )
            if not collection:
                # Collection 已被删除，禁用任务
                task.is_enabled = False
                task.last_run_status = "failed"
                task.last_run_result = {
                    "error": "target_collection_deleted",
                    "message": f"Collection '{task.target_collection_id}' no longer exists",
                }
                db.commit()
                return None
            return collection
        else:
            # create_new 模式：每次创建新 collection
            prefix = task.new_collection_prefix or task.name
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            title = f"{prefix} - {date_str}"
            slug = prefix.lower().replace(" ", "-")[:40]
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
            db.flush()
            return collection
