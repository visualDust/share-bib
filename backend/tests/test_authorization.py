import asyncio
import uuid

import pytest
from api import admin, auth, collections, crawl_tasks, import_tasks, papers, sdk, users
from api.auth import _sync_oauth_admin
from auth.jwt_handler import create_access_token
from auth.simple import get_password_hash
from crawl.executor import CrawlExecutor
from database import Base, get_db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from models import (
    ApiKey,
    Collection,
    CollectionPaper,
    CollectionPermission,
    CrawlTask,
    ImportTask,
    Paper,
    User,
    UserSetting,
)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from services.user_identity import suffix_oauth_username


@pytest.fixture()
def api_context(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'authorization.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    app = FastAPI()
    for router in (
        auth.router,
        admin.router,
        users.router,
        collections.router,
        papers.router,
        crawl_tasks.router,
        import_tasks.router,
        sdk.router,
    ):
        app.include_router(router)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    db = testing_session()
    owner = User(
        id="owner",
        username="owner",
        display_name="Owner",
        password_hash=get_password_hash("owner-password"),
        is_active=True,
        is_admin=True,
        token_version=0,
    )
    stranger = User(
        id="stranger",
        username="stranger",
        display_name="Stranger",
        password_hash=get_password_hash("stranger-password"),
        is_active=True,
        is_admin=False,
        token_version=0,
    )
    editor = User(
        id="editor",
        username="editor",
        display_name="Editor",
        password_hash=get_password_hash("editor-password"),
        is_active=True,
        is_admin=False,
        token_version=0,
    )
    db.add_all([owner, stranger, editor])
    db.commit()

    def token(user: User) -> str:
        return create_access_token(
            {
                "sub": user.id,
                "username": user.username,
                "ver": user.token_version,
            }
        )

    client = TestClient(app)
    context = {
        "client": client,
        "db": db,
        "owner": owner,
        "stranger": stranger,
        "editor": editor,
        "headers": {
            user.id: {"Authorization": f"Bearer {token(user)}"}
            for user in (owner, stranger, editor)
        },
        "token": token,
        "session_factory": testing_session,
    }
    yield context

    client.close()
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_collection(db, owner: User, collection_id: str, visibility: str = "private"):
    collection = Collection(
        id=collection_id,
        title=collection_id,
        created_by=owner.id,
        visibility=visibility,
        task_type="manual",
    )
    db.add(collection)
    db.commit()
    return collection


def add_paper(db, collection: Collection, title: str = "Private paper"):
    paper = Paper(id=str(uuid.uuid4()), title=title, status="accessible")
    db.add(paper)
    db.flush()
    db.add(
        CollectionPaper(collection_id=collection.id, paper_id=paper.id, display_order=0)
    )
    db.commit()
    return paper


def test_mutable_username_does_not_grant_admin(api_context):
    client = api_context["client"]
    owner = api_context["owner"]
    stranger = api_context["stranger"]
    headers = api_context["headers"]

    response = client.put(
        "/api/users/me",
        json={"username": "renamed-admin", "display_name": "Owner"},
        headers=headers[owner.id],
    )
    assert response.status_code == 200

    response = client.put(
        "/api/users/me",
        json={"username": "owner", "display_name": "Stranger"},
        headers=headers[stranger.id],
    )
    assert response.status_code == 200
    assert (
        client.get("/api/admin/users", headers=headers[stranger.id]).status_code == 403
    )
    assert client.get("/api/admin/users", headers=headers[owner.id]).status_code == 200


def test_private_paper_is_not_globally_readable_or_writable(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    stranger = api_context["stranger"]
    headers = api_context["headers"]
    collection = add_collection(db, owner, "private-library")
    paper = add_paper(db, collection)

    listed = client.get("/api/papers", headers=headers[stranger.id])
    assert listed.status_code == 200
    assert all(item["id"] != paper.id for item in listed.json())
    assert (
        client.get(f"/api/papers/{paper.id}", headers=headers[stranger.id]).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/papers/{paper.id}?collection_id={collection.id}",
            json={"title": "Stolen"},
            headers=headers[stranger.id],
        ).status_code
        == 403
    )
    db.refresh(paper)
    assert paper.title == "Private paper"


def test_collection_scoped_paper_update_uses_copy_on_write(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    headers = api_context["headers"]
    first = add_collection(db, owner, "first")
    second = add_collection(db, owner, "second")
    paper = add_paper(db, first, "Shared record")
    db.add(CollectionPaper(collection_id=second.id, paper_id=paper.id, display_order=0))
    db.commit()

    response = client.put(
        f"/api/papers/{paper.id}?collection_id={first.id}",
        json={"title": "First collection title"},
        headers=headers[owner.id],
    )
    assert response.status_code == 200
    updated_id = response.json()["id"]
    assert updated_id != paper.id

    first_link = db.query(CollectionPaper).filter_by(collection_id=first.id).one()
    second_link = db.query(CollectionPaper).filter_by(collection_id=second.id).one()
    assert first_link.paper_id == updated_id
    assert second_link.paper_id == paper.id
    assert db.get(Paper, paper.id).title == "Shared record"
    assert db.get(Paper, updated_id).title == "First collection title"


def test_collection_policy_and_collaborators_are_owner_only(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    headers = api_context["headers"]
    collection = add_collection(db, owner, "shared")
    db.add(
        CollectionPermission(
            collection_id=collection.id, user_id=editor.id, permission="edit"
        )
    )
    db.commit()

    editor_view = client.get(
        f"/api/collections/{collection.id}", headers=headers[editor.id]
    )
    assert editor_view.status_code == 200
    assert editor_view.json()["permissions"] == []

    owner_view = client.get(
        f"/api/collections/{collection.id}", headers=headers[owner.id]
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["permissions"][0]["user_id"] == editor.id

    response = client.put(
        f"/api/collections/{collection.id}",
        json={"allow_export": True},
        headers=headers[editor.id],
    )
    assert response.status_code == 403


def test_permission_upsert_keeps_one_effective_role(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    stranger = api_context["stranger"]
    headers = api_context["headers"]
    collection = add_collection(db, owner, "permissions")

    for permission in ("view", "edit"):
        response = client.post(
            f"/api/collections/{collection.id}/permissions",
            json={"user_id": stranger.id, "permission": permission},
            headers=headers[owner.id],
        )
        assert response.status_code in (200, 201)

    rows = (
        db.query(CollectionPermission)
        .filter_by(collection_id=collection.id, user_id=stranger.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].permission == "edit"


def test_crawl_task_requires_current_target_edit_permission(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    stranger = api_context["stranger"]
    editor = api_context["editor"]
    headers = api_context["headers"]
    collection = add_collection(db, owner, "crawl-target")
    payload = {
        "name": "Daily papers",
        "source_type": "arxiv_rss",
        "source_config": {"categories": ["cs.AI"]},
        "schedule_type": "daily",
        "target_mode": "append",
        "target_collection_id": collection.id,
        "duplicate_strategy": "skip",
    }

    assert (
        client.post(
            "/api/crawl-tasks", json=payload, headers=headers[stranger.id]
        ).status_code
        == 403
    )
    db.add(
        CollectionPermission(
            collection_id=collection.id, user_id=editor.id, permission="edit"
        )
    )
    db.commit()
    assert client.post(
        "/api/crawl-tasks", json=payload, headers=headers[editor.id]
    ).status_code in (200, 201)


def test_bibtex_scan_is_collection_scoped_and_user_scoped(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    stranger = api_context["stranger"]
    headers = api_context["headers"]
    collection = add_collection(db, owner, "scan-target")
    bibtex = b"@article{one, title={A Paper}, author={Researcher}}"

    denied = client.post(
        "/api/import/bibtex/scan",
        data={"collection_id": collection.id},
        files={"file": ("papers.bib", bibtex, "application/x-bibtex")},
        headers=headers[stranger.id],
    )
    assert denied.status_code == 403

    scan = client.post(
        "/api/import/bibtex/scan",
        data={"collection_id": collection.id},
        files={"file": ("papers.bib", bibtex, "application/x-bibtex")},
        headers=headers[owner.id],
    )
    assert scan.status_code == 200
    scan_id = scan.json()["scan_id"]
    stolen = client.post(
        "/api/import/bibtex",
        data={"scan_id": scan_id, "collection_name": "stolen"},
        headers=headers[stranger.id],
    )
    assert stolen.status_code == 404


def test_editor_dedup_cannot_discover_or_link_owner_private_paper(
    api_context, monkeypatch
):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    headers = api_context["headers"]
    monkeypatch.setattr(import_tasks, "SessionLocal", api_context["session_factory"])
    private_collection = add_collection(db, owner, "owners-private-library")
    private_paper = add_paper(db, private_collection, "Unpublished Finding")
    target = add_collection(db, owner, "shared-import-target")
    db.add(
        CollectionPermission(
            collection_id=target.id, user_id=editor.id, permission="edit"
        )
    )
    db.commit()
    bibtex = b"@article{private, title={Unpublished Finding}, author={Researcher}}"

    scan = client.post(
        "/api/import/bibtex/scan",
        data={"collection_id": target.id},
        files={"file": ("papers.bib", bibtex, "application/x-bibtex")},
        headers=headers[editor.id],
    )
    assert scan.status_code == 200
    assert scan.json()["duplicates"] == []

    imported = client.post(
        f"/api/import/bibtex/{target.id}",
        files={"file": ("papers.bib", bibtex, "application/x-bibtex")},
        headers=headers[editor.id],
    )
    assert imported.status_code == 200
    db.expire_all()
    target_links = db.query(CollectionPaper).filter_by(collection_id=target.id).all()
    assert len(target_links) == 1
    assert target_links[0].paper_id != private_paper.id


def test_executor_rechecks_permission_after_awaited_fetch(api_context, monkeypatch):
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    target = add_collection(db, owner, "awaited-revocation-target")
    permission = CollectionPermission(
        collection_id=target.id, user_id=editor.id, permission="edit"
    )
    task = CrawlTask(
        user_id=editor.id,
        name="Awaited revocation",
        source_type="arxiv_rss",
        source_config={"categories": ["cs.AI"]},
        schedule_type="daily",
        time_range="1d",
        target_mode="append",
        target_collection_id=target.id,
        duplicate_strategy="skip",
        is_enabled=True,
    )
    db.add_all([permission, task])
    db.commit()
    session_factory = api_context["session_factory"]

    class RevokingSource:
        async def fetch(self, *_args):
            revoker = session_factory()
            try:
                concurrent_permission = (
                    revoker.query(CollectionPermission)
                    .filter_by(collection_id=target.id, user_id=editor.id)
                    .one()
                )
                revoker.delete(concurrent_permission)
                revoker.commit()
            finally:
                revoker.close()
            return []

    monkeypatch.setattr("crawl.executor.get_source", lambda _source: RevokingSource())
    result = asyncio.run(CrawlExecutor().execute(task, db))
    assert result["error"] == "target_permission_revoked"


@pytest.mark.parametrize(
    ("concurrent_change", "expected_error"),
    (
        ("configuration", "task_changed_during_execution"),
        ("disabled", "task_disabled"),
    ),
)
def test_executor_discards_results_when_task_changes_during_fetch(
    api_context, monkeypatch, concurrent_change, expected_error
):
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    first_target = add_collection(db, owner, "original-crawl-target")
    second_target = add_collection(db, owner, "changed-crawl-target")
    db.add_all(
        [
            CollectionPermission(
                collection_id=first_target.id, user_id=editor.id, permission="edit"
            ),
            CollectionPermission(
                collection_id=second_target.id, user_id=editor.id, permission="edit"
            ),
        ]
    )
    task = CrawlTask(
        user_id=editor.id,
        name="Changing task",
        source_type="arxiv_rss",
        source_config={"categories": ["cs.AI"]},
        schedule_type="daily",
        time_range="1d",
        target_mode="append",
        target_collection_id=first_target.id,
        duplicate_strategy="skip",
        is_enabled=True,
    )
    db.add(task)
    db.commit()
    session_factory = api_context["session_factory"]
    task_id = task.id
    second_target_id = second_target.id

    class FetchedPaper:
        title = "Fetched Under Old Configuration"

        @staticmethod
        def to_paper_dict():
            return {"title": FetchedPaper.title, "status": "accessible"}

    class MutatingSource:
        async def fetch(self, *_args):
            updater = session_factory()
            try:
                concurrent_task = updater.query(CrawlTask).filter_by(id=task_id).one()
                if concurrent_change == "configuration":
                    concurrent_task.source_config = {"categories": ["cs.LG"]}
                    concurrent_task.target_collection_id = second_target_id
                else:
                    concurrent_task.is_enabled = False
                updater.commit()
            finally:
                updater.close()
            return [FetchedPaper()]

    monkeypatch.setattr("crawl.executor.get_source", lambda _source: MutatingSource())
    result = asyncio.run(CrawlExecutor().execute(task, db))

    assert result["error"] == expected_error
    assert db.query(Paper).filter_by(title=FetchedPaper.title).first() is None
    assert db.query(CollectionPaper).count() == 0


def test_arxiv_import_rechecks_permission_after_network_wait(api_context, monkeypatch):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    headers = api_context["headers"]
    target = add_collection(db, owner, "arxiv-revocation-target")
    permission = CollectionPermission(
        collection_id=target.id, user_id=editor.id, permission="edit"
    )
    db.add(permission)
    db.commit()
    session_factory = api_context["session_factory"]

    async def fetch_then_revoke(_arxiv_id):
        revoker = session_factory()
        try:
            concurrent_permission = (
                revoker.query(CollectionPermission)
                .filter_by(collection_id=target.id, user_id=editor.id)
                .one()
            )
            revoker.delete(concurrent_permission)
            revoker.commit()
        finally:
            revoker.close()
        return {
            "title": "Fetched During Revocation",
            "authors": ["Researcher"],
            "arxiv_id": "2401.12345",
            "status": "accessible",
        }

    monkeypatch.setattr(import_tasks, "_fetch_arxiv_metadata", fetch_then_revoke)
    response = client.post(
        f"/api/import/arxiv/{target.id}",
        json={"url": "https://arxiv.org/abs/2401.12345"},
        headers=headers[editor.id],
    )
    assert response.status_code == 403
    assert db.query(Paper).filter_by(title="Fetched During Revocation").first() is None


def test_append_import_rechecks_permission_after_parse(api_context, monkeypatch):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    headers = api_context["headers"]
    session_factory = api_context["session_factory"]
    target = add_collection(db, owner, "parse-revocation-target")
    db.add(
        CollectionPermission(
            collection_id=target.id, user_id=editor.id, permission="edit"
        )
    )
    db.commit()

    def parse_then_revoke(_content):
        revoker = session_factory()
        try:
            concurrent_permission = (
                revoker.query(CollectionPermission)
                .filter_by(collection_id=target.id, user_id=editor.id)
                .one()
            )
            revoker.delete(concurrent_permission)
            revoker.commit()
        finally:
            revoker.close()
        return [
            {
                "_entry_id": "revoked-entry",
                "title": "Parsed During Revocation",
                "authors": ["Researcher"],
                "status": "accessible",
            }
        ]

    monkeypatch.setattr(import_tasks, "SessionLocal", session_factory)
    monkeypatch.setattr(import_tasks, "parse_bibtex_content", parse_then_revoke)
    response = client.post(
        f"/api/import/bibtex/{target.id}",
        files={"file": ("papers.bib", "@article{x}", "application/x-bibtex")},
        headers=headers[editor.id],
    )
    assert response.status_code == 200

    task = db.query(ImportTask).filter_by(id=response.json()["task_id"]).one()
    db.refresh(task)
    assert task.status == "failed"
    assert "can no longer edit" in task.result["error"]
    assert db.query(Paper).filter_by(title="Parsed During Revocation").first() is None


def test_oauth_admin_sync_preserves_manual_roles_and_revokes_oauth_roles():
    setup_admin = User(is_admin=True, admin_source="setup", token_version=0)
    _sync_oauth_admin(setup_admin, False)
    assert setup_admin.is_admin is True
    assert setup_admin.admin_source == "setup"
    assert setup_admin.token_version == 0

    oauth_admin = User(is_admin=True, admin_source="oauth", token_version=2)
    _sync_oauth_admin(oauth_admin, False)
    assert oauth_admin.is_admin is False
    assert oauth_admin.admin_source is None
    assert oauth_admin.token_version == 3

    oauth_member = User(is_admin=False, token_version=4)
    _sync_oauth_admin(oauth_member, True)
    assert oauth_member.is_admin is True
    assert oauth_member.admin_source == "oauth"
    assert oauth_member.token_version == 5


def test_oauth_username_suffix_stays_within_model_limit():
    candidate = suffix_oauth_username("a" * 64, 123)
    assert candidate == f"{'a' * 60}_123"
    assert len(candidate) == 64


def test_branded_and_legacy_api_keys_authenticate(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]

    assert ApiKey.generate_key().startswith("sb_")
    for index, plain_key in enumerate(
        ("sb_12345678branded-secret", "pc_87654321legacy-secret")
    ):
        db.add(
            ApiKey(
                user_id=owner.id,
                name=f"key-{index}",
                key_hash=ApiKey.hash_key(plain_key),
                key_prefix=plain_key[:11],
                is_active=True,
            )
        )
    db.commit()

    for plain_key in ("sb_12345678branded-secret", "pc_87654321legacy-secret"):
        response = client.get("/api/sdk/me", headers={"X-API-Key": plain_key})
        assert response.status_code == 200
        assert response.json()["id"] == owner.id


def test_password_change_revokes_existing_jwt(api_context):
    client = api_context["client"]
    owner = api_context["owner"]
    headers = api_context["headers"]

    response = client.put(
        "/api/users/me/change-password",
        json={"old_password": "owner-password", "new_password": "new-owner-password"},
        headers=headers[owner.id],
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me", headers=headers[owner.id]).status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"username": owner.username, "password": "new-owner-password"},
    )
    assert login.status_code == 200
    new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200


def test_new_account_fields_are_validated(api_context):
    client = api_context["client"]
    owner = api_context["owner"]
    headers = api_context["headers"]

    response = client.post(
        "/api/admin/users",
        json={"username": "bad/name", "password": "short", "email": "not-email"},
        headers=headers[owner.id],
    )
    assert response.status_code == 422


def test_executor_disables_task_after_target_permission_is_revoked(api_context):
    db = api_context["db"]
    owner = api_context["owner"]
    editor = api_context["editor"]
    collection = add_collection(db, owner, "revoked-target")
    permission = CollectionPermission(
        collection_id=collection.id, user_id=editor.id, permission="edit"
    )
    task = CrawlTask(
        user_id=editor.id,
        name="Revoked task",
        source_type="arxiv_rss",
        source_config={"categories": ["cs.AI"]},
        schedule_type="daily",
        time_range="1d",
        target_mode="append",
        target_collection_id=collection.id,
        duplicate_strategy="skip",
        is_enabled=True,
    )
    db.add_all([permission, task])
    db.commit()

    db.delete(permission)
    db.commit()
    assert CrawlExecutor()._resolve_collection(task, db) is None
    assert task.is_enabled is False
    assert task.last_run_result["error"] == "target_permission_revoked"


def test_sdk_does_not_expose_global_orphan_papers(api_context):
    db = api_context["db"]
    stranger = api_context["stranger"]
    orphan = Paper(title="Unreferenced secret", status="no_access")
    db.add(orphan)
    db.commit()

    with pytest.raises(Exception) as error:
        sdk.get_paper(orphan.id, stranger, db)
    assert getattr(error.value, "status_code", None) == 404


def test_admin_delete_revokes_credentials_and_disables_foreign_tasks(api_context):
    client = api_context["client"]
    db = api_context["db"]
    owner = api_context["owner"]
    stranger = api_context["stranger"]
    editor = api_context["editor"]
    headers = api_context["headers"]
    collection = add_collection(db, stranger, "deleted-user-target")
    owned_task = CrawlTask(
        user_id=stranger.id,
        name="Owned task",
        source_type="arxiv_rss",
        source_config={"categories": ["cs.AI"]},
        schedule_type="daily",
        time_range="1d",
        target_mode="append",
        target_collection_id=collection.id,
        duplicate_strategy="skip",
        is_enabled=True,
    )
    foreign_task = CrawlTask(
        user_id=editor.id,
        name="Foreign task",
        source_type="arxiv_rss",
        source_config={"categories": ["cs.AI"]},
        schedule_type="daily",
        time_range="1d",
        target_mode="append",
        target_collection_id=collection.id,
        duplicate_strategy="skip",
        is_enabled=True,
    )
    db.add_all(
        [
            owned_task,
            foreign_task,
            ApiKey(
                user_id=stranger.id,
                name="credential",
                key_hash="hash",
                key_prefix="pc_test",
                is_active=True,
            ),
            UserSetting(user_id=stranger.id, key="secret", value="value"),
        ]
    )
    db.commit()
    stranger_id = stranger.id
    foreign_task_id = foreign_task.id

    response = client.request(
        "DELETE",
        f"/api/admin/users/{stranger_id}",
        json={"mode": "delete"},
        headers=headers[owner.id],
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.get(User, stranger_id) is None
    assert db.query(ApiKey).filter_by(user_id=stranger_id).count() == 0
    assert db.query(UserSetting).filter_by(user_id=stranger_id).count() == 0
    assert db.query(CrawlTask).filter_by(user_id=stranger_id).count() == 0
    retained_task = db.get(CrawlTask, foreign_task_id)
    assert retained_task is not None
    assert retained_task.is_enabled is False
    assert retained_task.target_collection_id is None
