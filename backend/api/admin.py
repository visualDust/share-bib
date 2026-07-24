from auth.deps import get_admin_user
from auth.simple import get_password_hash
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from models import (
    ApiKey,
    Collection,
    CollectionPermission,
    CrawlTask,
    CrawlTaskRun,
    ImportTask,
    User,
    UserPaperMeta,
    UserSetting,
)
from schemas.user import (
    AdminDeleteUser,
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    users = db.query(User).order_by(User.created_at).all()
    return [
        AdminUserOut(
            id=u.id,
            username=u.username,
            email=u.email,
            display_name=u.display_name,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/users/search")
def admin_search_users(
    q: str = Query(..., min_length=1),
    exclude: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    query = db.query(User).filter(User.username.ilike(f"%{q}%"), User.is_active)
    if exclude:
        query = query.filter(User.id != exclude)
    users = query.limit(10).all()
    return [
        {"user_id": u.id, "username": u.username, "display_name": u.display_name}
        for u in users
    ]


@router.post("/users", response_model=AdminUserOut)
def create_user(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=body.username,
        email=body.email,
        display_name=body.display_name or body.username,
        password_hash=get_password_hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AdminUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/users/check")
def check_user_field(
    field: str = Query(...),
    value: str = Query(...),
    exclude_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Check if a user field value is already taken. Returns {available: bool}."""
    if field == "username":
        q = db.query(User).filter(User.username == value)
    elif field == "email":
        if not value:
            return {"available": True}
        q = db.query(User).filter(User.email == value)
    else:
        raise HTTPException(status_code=400, detail="Invalid field")
    if exclude_id:
        q = q.filter(User.id != exclude_id)
    return {"available": q.first() is None}


@router.put("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: str,
    body: AdminUserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.username is not None and body.username != user.username:
        if (
            db.query(User)
            .filter(User.username == body.username, User.id != user_id)
            .first()
        ):
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = body.username

    if body.email is not None and body.email != user.email:
        if (
            body.email
            and db.query(User)
            .filter(User.email == body.email, User.id != user_id)
            .first()
        ):
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = body.email or None

    if body.display_name is not None:
        user.display_name = body.display_name

    db.commit()
    db.refresh(user)
    return AdminUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.put("/users/{user_id}/reset-password")
def reset_password(
    user_id: str,
    body: AdminPasswordReset,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(body.new_password)
    user.token_version += 1
    db.commit()
    return {"detail": "Password reset successfully"}


@router.put("/users/{user_id}/toggle-active")
def toggle_active(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")

    user.is_active = not user.is_active
    user.token_version += 1
    db.commit()
    return {
        "detail": f"User {'enabled' if user.is_active else 'disabled'}",
        "is_active": user.is_active,
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    body: AdminDeleteUser = AdminDeleteUser(),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    if body.mode == "transfer":
        if not body.transfer_to:
            raise HTTPException(status_code=400, detail="transfer_to is required")
        target = db.query(User).filter(User.id == body.transfer_to).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found")
        if target.id == user.id:
            raise HTTPException(
                status_code=400, detail="Cannot transfer to the same user"
            )
        db.query(Collection).filter(Collection.created_by == user.id).update(
            {"created_by": target.id}
        )
        existing = {
            p.collection_id: p
            for p in db.query(CollectionPermission)
            .filter(CollectionPermission.user_id == target.id)
            .all()
        }
        for perm in (
            db.query(CollectionPermission)
            .filter(CollectionPermission.user_id == user.id)
            .all()
        ):
            target_owns_collection = (
                db.query(Collection.id)
                .filter(
                    Collection.id == perm.collection_id,
                    Collection.created_by == target.id,
                )
                .first()
                is not None
            )
            if target_owns_collection:
                db.delete(perm)
                continue
            target_perm = existing.get(perm.collection_id)
            if target_perm:
                if perm.permission == "edit" and target_perm.permission != "edit":
                    target_perm.permission = "edit"
                db.delete(perm)
            else:
                perm.user_id = target.id
                existing[perm.collection_id] = perm
        db.query(ImportTask).filter(ImportTask.user_id == user.id).update(
            {"user_id": target.id}
        )
        db.query(CrawlTask).filter(CrawlTask.user_id == user.id).update(
            {"user_id": target.id}
        )
    else:
        owned_collection_ids = [
            collection_id
            for (collection_id,) in db.query(Collection.id)
            .filter(Collection.created_by == user.id)
            .all()
        ]
        owned_task_ids = [
            task_id
            for (task_id,) in db.query(CrawlTask.id)
            .filter(CrawlTask.user_id == user.id)
            .all()
        ]
        if owned_task_ids:
            db.query(CrawlTaskRun).filter(
                CrawlTaskRun.task_id.in_(owned_task_ids)
            ).delete(synchronize_session=False)
        db.query(CrawlTask).filter(CrawlTask.user_id == user.id).delete(
            synchronize_session=False
        )
        if owned_collection_ids:
            db.query(CrawlTask).filter(
                CrawlTask.target_collection_id.in_(owned_collection_ids)
            ).update(
                {
                    "is_enabled": False,
                    "target_collection_id": None,
                    "last_run_status": "failed",
                    "last_run_result": {"error": "target_collection_deleted"},
                },
                synchronize_session=False,
            )
        db.query(CollectionPermission).filter(
            CollectionPermission.user_id == user.id
        ).delete()
        db.query(ImportTask).filter(ImportTask.user_id == user.id).delete()
        for col in db.query(Collection).filter(Collection.created_by == user.id).all():
            db.delete(col)

    db.query(UserPaperMeta).filter(UserPaperMeta.user_id == user.id).delete()
    # Credentials and private source settings are revoked, never transferred.
    db.query(ApiKey).filter(ApiKey.user_id == user.id).delete()
    db.query(UserSetting).filter(UserSetting.user_id == user.id).delete()
    db.delete(user)
    db.commit()

    return {"detail": "User deleted"}
