import uuid
import re
import json
import logging
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Body,
    Request,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from database import get_db, SessionLocal
from models import User, Paper, Collection, CollectionPaper, ImportTask
from import_module.bibtex_parser import parse_bibtex_content
from services.deduplication import find_duplicate_paper

router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)

# In-memory cache for scan results (expires after 30 minutes)
_scan_cache: dict[str, dict] = {}

# Simple backend i18n for import-related strings
_MESSAGES = {
    "zh": {
        "bib_description": "从 BibTeX 文件导入的论文集合",
        "group_imported": "导入的论文",
        "group_arxiv": "arXiv 导入",
        "already_in_collection": "已在集合中",
        "paper_already_in_collection": "论文已在集合中",
        "cannot_parse_arxiv": "无法从链接中解析 arXiv ID",
        "fetch_arxiv_failed": "获取 arXiv 元数据失败",
    },
    "en": {
        "bib_description": "Paper collection imported from BibTeX file",
        "group_imported": "Imported",
        "group_arxiv": "arXiv Import",
        "already_in_collection": "Already in collection",
        "paper_already_in_collection": "Paper already in collection",
        "cannot_parse_arxiv": "Cannot parse arXiv ID from URL",
        "fetch_arxiv_failed": "Failed to fetch arXiv metadata",
    },
}


def _get_lang(accept_language: str | None) -> str:
    if accept_language and accept_language.lower().startswith("zh"):
        return "zh"
    return "en"


def _msg(lang: str, key: str) -> str:
    return _MESSAGES.get(lang, _MESSAGES["en"]).get(key, key)


def _cleanup_expired_scans():
    """Remove expired scan results from cache."""
    now = datetime.now(timezone.utc)
    expired = [
        k
        for k, v in _scan_cache.items()
        if now - v["timestamp"] > timedelta(minutes=30)
    ]
    for k in expired:
        del _scan_cache[k]


def _process_bibtex(
    task_id: str,
    content: str,
    collection_name: str,
    user_id: str,
    duplicate_strategy: str = "keep_existing",
    duplicate_decisions: dict[str, str] | None = None,
    lang: str = "en",
):
    """Background task to process BibTeX import with duplicate strategy."""
    db = SessionLocal()
    try:
        task = db.query(ImportTask).filter(ImportTask.id == task_id).first()
        if not task:
            return

        papers_data = parse_bibtex_content(content)
        total = len(papers_data)
        success = 0
        skipped = 0
        errors = []
        duplicates_merged = []

        # Create collection
        slug = collection_name.lower().replace(" ", "-")[:50]
        cid = f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        # Ensure unique
        if db.query(Collection).filter(Collection.id == cid).first():
            cid = f"{cid}-{uuid.uuid4().hex[:4]}"

        collection = Collection(
            id=cid,
            title=collection_name,
            description=_msg(lang, "bib_description"),
            created_by=user_id,
            visibility="private",
            task_type="bib_import",
            task_source="user_upload",
            task_source_display=collection_name,
        )
        db.add(collection)
        db.flush()

        for pd in papers_data:
            entry_id = pd.pop("_entry_id", "unknown")
            try:
                # Use collection owner for scoped deduplication
                existing, dup_info = find_duplicate_paper(db, pd, owner_user_id=user_id)

                if existing and dup_info:
                    # Determine action based on strategy
                    if duplicate_strategy == "manual":
                        # Use user's decision from manual review
                        decision = (duplicate_decisions or {}).get(
                            entry_id, "keep_existing"
                        )
                    else:
                        # Auto mode: use strategy directly
                        decision = duplicate_strategy  # "keep_existing" or "use_new"

                    if decision == "skip":
                        skipped += 1
                        errors.append(
                            {"entry_id": entry_id, "reason": "Skipped by user"}
                        )
                        continue
                    elif decision == "use_new":
                        # Update existing paper with new data
                        for key, value in pd.items():
                            if value is not None:  # Only update non-null fields
                                setattr(existing, key, value)
                        paper = existing
                    else:  # keep_existing
                        paper = existing

                    duplicates_merged.append(dup_info.dict())
                else:
                    # No duplicate found, create new paper
                    paper = Paper(**pd)
                    db.add(paper)
                    db.flush()

                # Add to collection
                cp_exists = (
                    db.query(CollectionPaper)
                    .filter(
                        CollectionPaper.collection_id == cid,
                        CollectionPaper.paper_id == paper.id,
                    )
                    .first()
                )
                if not cp_exists:
                    cp = CollectionPaper(
                        collection_id=cid,
                        paper_id=paper.id,
                        group_name=_msg(lang, "group_imported"),
                        group_tag="imported",
                        section_name="All Papers",
                        display_order=success,
                    )
                    db.add(cp)
                success += 1
            except Exception as e:
                logger.error(f"Error importing entry {entry_id}: {e}")
                errors.append({"entry_id": entry_id, "reason": str(e)})
                skipped += 1

        task.status = "completed"
        task.collection_id = cid
        task.result = {
            "collection_id": cid,
            "progress": {
                "total": total,
                "processed": total,
                "success": success,
                "skipped": skipped,
            },
            "errors": errors,
            "duplicates": duplicates_merged,
        }
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.error(f"Import task {task_id} failed: {e}")
        task = db.query(ImportTask).filter(ImportTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.result = {"error": str(e)}
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _process_bibtex_append(
    task_id: str,
    content: str,
    collection_id: str,
    user_id: str,
    duplicate_strategy: str = "keep_existing",
    skip_collection_duplicates: bool = True,
    duplicate_decisions: dict[str, str] | None = None,
    lang: str = "en",
):
    """Background task to append BibTeX papers to an existing collection with strategy-based dedup control."""
    db = SessionLocal()
    try:
        task = db.query(ImportTask).filter(ImportTask.id == task_id).first()
        if not task:
            return

        # Get collection to determine owner
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")
        owner_user_id = collection.created_by

        papers_data = parse_bibtex_content(content)
        total = len(papers_data)
        success = 0
        skipped = 0
        errors = []
        duplicates_merged = []

        max_order = (
            db.query(func.max(CollectionPaper.display_order))
            .filter(CollectionPaper.collection_id == collection_id)
            .scalar()
            or 0
        )

        for pd in papers_data:
            entry_id = pd.pop("_entry_id", "unknown")
            try:
                # Use collection owner for scoped deduplication
                existing, dup_info = find_duplicate_paper(
                    db, pd, owner_user_id=owner_user_id
                )

                if existing and dup_info:
                    # Determine action based on strategy
                    if duplicate_strategy == "manual":
                        decision = (duplicate_decisions or {}).get(
                            entry_id, "keep_existing"
                        )
                    else:
                        decision = duplicate_strategy

                    if decision == "skip":
                        skipped += 1
                        errors.append(
                            {"entry_id": entry_id, "reason": "Skipped by user"}
                        )
                        continue
                    elif decision == "use_new":
                        for key, value in pd.items():
                            if value is not None:
                                setattr(existing, key, value)
                        paper = existing
                    else:  # keep_existing
                        paper = existing

                    duplicates_merged.append(dup_info.dict())
                else:
                    paper = Paper(**pd)
                    db.add(paper)
                    db.flush()

                # Check if already in collection
                cp_exists = (
                    db.query(CollectionPaper)
                    .filter(
                        CollectionPaper.collection_id == collection_id,
                        CollectionPaper.paper_id == paper.id,
                    )
                    .first()
                )
                if cp_exists:
                    if skip_collection_duplicates:
                        skipped += 1
                        errors.append(
                            {
                                "entry_id": entry_id,
                                "reason": _msg(lang, "already_in_collection"),
                            }
                        )
                        continue

                max_order += 1
                cp = CollectionPaper(
                    collection_id=collection_id,
                    paper_id=paper.id,
                    group_name=_msg(lang, "group_imported"),
                    group_tag="imported",
                    section_name="All Papers",
                    display_order=max_order,
                )
                db.add(cp)
                success += 1
            except Exception as e:
                logger.error(f"Error importing entry {entry_id}: {e}")
                errors.append({"entry_id": entry_id, "reason": str(e)})
                skipped += 1

        task.status = "completed"
        task.collection_id = collection_id
        task.result = {
            "collection_id": collection_id,
            "progress": {
                "total": total,
                "processed": total,
                "success": success,
                "skipped": skipped,
            },
            "errors": errors,
            "duplicates": duplicates_merged,
        }
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.error(f"Import append task {task_id} failed: {e}")
        task = db.query(ImportTask).filter(ImportTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.result = {"error": str(e)}
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/bibtex/scan")
async def scan_bibtex_for_duplicates(
    request: Request,
    file: UploadFile = File(...),
    collection_id: str = Form(None),  # Optional: for collection-scoped dedup
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan BibTeX file for duplicates without importing.

    If collection_id is provided, uses collection owner for scoped deduplication.
    Otherwise, uses current user for scoped deduplication.
    """
    if not file.filename or not file.filename.endswith(".bib"):
        raise HTTPException(status_code=400, detail="Only .bib files are accepted")

    content = await file.read()
    text = None
    for encoding in ("utf-8", "latin-1", "gbk"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="Unable to decode file")

    # Determine owner for scoped deduplication
    owner_user_id = current_user.id
    if collection_id:
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if collection:
            owner_user_id = collection.created_by

    papers_data = parse_bibtex_content(text)
    duplicates: list[dict] = []

    for pd in papers_data:
        existing, dup_info = find_duplicate_paper(db, pd, owner_user_id=owner_user_id)
        if existing and dup_info:
            duplicates.append(dup_info.dict())

    # Store in cache
    scan_id = str(uuid.uuid4())
    _cleanup_expired_scans()
    _scan_cache[scan_id] = {
        "content": text,
        "timestamp": datetime.now(timezone.utc),
        "duplicates": duplicates,
    }

    return {
        "scan_id": scan_id,
        "total": len(papers_data),
        "duplicates": duplicates,
        "new_papers": len(papers_data) - len(duplicates),
    }


@router.post("/bibtex")
async def import_bibtex(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    collection_name: str = Form(None),
    scan_id: str = Form(None),
    duplicate_strategy: str = Form("keep_existing"),
    duplicate_decisions: str = Form(None),
    skip_dedup: bool = Form(None),  # Backward compatibility
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get content from file or scan cache
    if scan_id:
        if scan_id not in _scan_cache:
            raise HTTPException(status_code=404, detail="Scan expired or not found")
        text = _scan_cache[scan_id]["content"]
        # Extract filename from scan if available
        if not collection_name:
            collection_name = "Imported Collection"
    else:
        if not file:
            raise HTTPException(status_code=400, detail="File or scan_id required")
        if not file.filename or not file.filename.endswith(".bib"):
            raise HTTPException(status_code=400, detail="Only .bib files are accepted")

        content = await file.read()
        text = None
        for encoding in ("utf-8", "latin-1", "gbk"):
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise HTTPException(status_code=400, detail="Unable to decode file")

        if not collection_name:
            collection_name = (
                file.filename.rsplit(".", 1)[0]
                .replace("_", " ")
                .replace("-", " ")
                .title()
            )

    # Backward compatibility: map old skip_dedup to new duplicate_strategy
    if skip_dedup is not None:
        duplicate_strategy = "use_new" if skip_dedup else "keep_existing"

    decisions = json.loads(duplicate_decisions) if duplicate_decisions else None

    task_id = str(uuid.uuid4())
    task = ImportTask(
        id=task_id,
        user_id=current_user.id,
        task_type="bibtex_import",
        status="processing",
    )
    db.add(task)
    db.commit()

    background_tasks.add_task(
        _process_bibtex,
        task_id,
        text,
        collection_name,
        current_user.id,
        duplicate_strategy,
        decisions,
        _get_lang(request.headers.get("accept-language")),
    )
    return {"task_id": task_id, "status": "processing", "message": "Import started"}


@router.post("/bibtex/{collection_id}")
async def import_bibtex_to_collection(
    collection_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    scan_id: str = Form(None),
    duplicate_strategy: str = Form("keep_existing"),
    skip_collection_duplicates: bool = Form(True),
    duplicate_decisions: str = Form(None),
    skip_dedup: bool = Form(None),  # Backward compatibility
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.permission_service import check_collection_permission

    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get content from file or scan cache
    if scan_id:
        if scan_id not in _scan_cache:
            raise HTTPException(status_code=404, detail="Scan expired or not found")
        text = _scan_cache[scan_id]["content"]
    else:
        if not file:
            raise HTTPException(status_code=400, detail="File or scan_id required")
        if not file.filename or not file.filename.endswith(".bib"):
            raise HTTPException(status_code=400, detail="Only .bib files are accepted")

        content = await file.read()
        text = None
        for encoding in ("utf-8", "latin-1", "gbk"):
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise HTTPException(status_code=400, detail="Unable to decode file")

    # Backward compatibility
    if skip_dedup is not None:
        duplicate_strategy = "use_new" if skip_dedup else "keep_existing"

    decisions = json.loads(duplicate_decisions) if duplicate_decisions else None

    task_id = str(uuid.uuid4())
    task = ImportTask(
        id=task_id,
        user_id=current_user.id,
        task_type="bibtex_append",
        status="processing",
    )
    db.add(task)
    db.commit()

    background_tasks.add_task(
        _process_bibtex_append,
        task_id,
        text,
        collection_id,
        current_user.id,
        duplicate_strategy,
        skip_collection_duplicates,
        decisions,
        _get_lang(request.headers.get("accept-language")),
    )
    return {"task_id": task_id, "status": "processing", "message": "Import started"}


def _parse_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from various URL formats."""
    # https://arxiv.org/abs/2301.12345
    # https://arxiv.org/pdf/2301.12345
    # https://arxiv.org/abs/2301.12345v2
    # 2301.12345
    m = re.search(r"(?:arxiv\.org/(?:abs|pdf|html)/)?(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    if m:
        return m.group(1)
    # Old format: arxiv.org/abs/cs/0601001
    m = re.search(r"(?:arxiv\.org/(?:abs|pdf)/)?([a-z-]+/\d{7}(?:v\d+)?)", url)
    if m:
        return m.group(1)
    return None


async def _fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch paper metadata from arXiv API."""
    import asyncio

    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    headers = {"User-Agent": "share-bib/1.0 (https://github.com/visualDust/share-bib)"}
    async with httpx.AsyncClient(timeout=30) as http:
        for attempt in range(3):
            resp = await http.get(api_url, headers=headers)
            if resp.status_code == 429:
                await asyncio.sleep(3 * (attempt + 1))
                continue
            resp.raise_for_status()
            break
        else:
            resp.raise_for_status()

    import xml.etree.ElementTree as ET

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(resp.text)
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError("Paper not found on arXiv")

    # Check for error
    id_el = entry.find("atom:id", ns)
    if id_el is not None and "error" in (id_el.text or "").lower():
        raise ValueError("Paper not found on arXiv")

    title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
    if not title:
        raise ValueError("Paper not found on arXiv")

    abstract = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")
    authors = [
        a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)
    ]

    # Year from published date
    published = entry.findtext("atom:published", "", ns)
    year = int(published[:4]) if published else None

    # Category as venue
    primary_cat = entry.find("arxiv:primary_category", ns)
    venue = primary_cat.get("term", "") if primary_cat is not None else ""

    # DOI
    doi_el = entry.find("arxiv:doi", ns)
    doi = doi_el.text if doi_el is not None else None

    # Strip version from arxiv_id for canonical form
    clean_id = re.sub(r"v\d+$", "", arxiv_id)

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "year": year,
        "venue": venue,
        "arxiv_id": clean_id,
        "doi": doi,
        "url_arxiv": f"https://arxiv.org/abs/{clean_id}",
        "url_pdf": f"https://arxiv.org/pdf/{clean_id}.pdf",
        "status": "accessible",
    }


@router.post("/arxiv/{collection_id}")
async def import_arxiv_to_collection(
    collection_id: str,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.permission_service import check_collection_permission

    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    lang = _get_lang(request.headers.get("accept-language"))

    arxiv_id = _parse_arxiv_id(url)
    if not arxiv_id:
        raise HTTPException(status_code=400, detail=_msg(lang, "cannot_parse_arxiv"))

    try:
        meta = await _fetch_arxiv_metadata(arxiv_id)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"{_msg(lang, 'fetch_arxiv_failed')}: {e}"
        )

    # Dedup: check if paper already exists using collection-scoped deduplication
    owner_user_id = c.created_by
    existing, dup_info = find_duplicate_paper(db, meta, owner_user_id=owner_user_id)
    if existing:
        paper = existing
    else:
        paper = Paper(**meta)
        db.add(paper)
        db.flush()

    # Check if already in collection
    cp_exists = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper.id,
        )
        .first()
    )
    if cp_exists:
        return {
            "ok": True,
            "paper_id": paper.id,
            "skipped": True,
            "message": _msg(lang, "paper_already_in_collection"),
        }

    max_order = (
        db.query(func.max(CollectionPaper.display_order))
        .filter(CollectionPaper.collection_id == collection_id)
        .scalar()
        or 0
    )

    cp = CollectionPaper(
        collection_id=collection_id,
        paper_id=paper.id,
        group_name=_msg(lang, "group_arxiv"),
        group_tag="arxiv",
        section_name="All Papers",
        display_order=max_order + 1,
    )
    db.add(cp)
    db.commit()

    return {"ok": True, "paper_id": paper.id, "title": meta["title"], "skipped": False}


@router.get("/tasks")
def list_import_tasks(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    tasks = (
        db.query(ImportTask)
        .filter(ImportTask.user_id == current_user.id)
        .order_by(ImportTask.created_at.desc())
        .all()
    )
    return [
        {
            "task_id": t.id,
            "status": t.status,
            "task_type": t.task_type,
            "result": t.result,
            "created_at": t.created_at,
            "completed_at": t.completed_at,
        }
        for t in tasks
    ]


@router.get("/tasks/{task_id}")
def get_import_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = (
        db.query(ImportTask)
        .filter(ImportTask.id == task_id, ImportTask.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.id,
        "status": task.status,
        "task_type": task.task_type,
        "result": task.result,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }
