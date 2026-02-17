from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from auth.deps import get_current_user
from auth.simple import verify_password, get_password_hash
from database import get_db
from models import User, Collection, CollectionPermission, CollectionPaper, Paper
from schemas import UserBrief
from schemas.collection import CollectionListOut, StatsOut
from schemas.user import UserBrief as UserBriefSchema, ChangePassword

router = APIRouter(prefix="/api/users", tags=["users"])


class UpdateUserProfile(BaseModel):
    username: str
    display_name: str | None = None
    email: str | None = None


@router.get("/search", response_model=list[UserBrief])
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = (
        db.query(User)
        .filter(User.username.ilike(f"%{q}%"), User.id != current_user.id)
        .limit(10)
        .all()
    )
    return [
        UserBrief(user_id=u.id, username=u.username, display_name=u.display_name)
        for u in users
    ]


def _collection_stats(db: Session, collection_id: str) -> StatsOut:
    cps = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [cp.paper_id for cp in cps]
    if not paper_ids:
        return StatsOut()
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    accessible = sum(1 for p in papers if p.status == "accessible")
    return StatsOut(
        total=len(papers), accessible=accessible, no_access=len(papers) - accessible
    )


@router.get("/{username}/profile")
def get_user_profile(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    own_collections = db.query(Collection).filter(Collection.created_by == user.id)

    if current_user.id == user.id:
        visible = own_collections.order_by(Collection.created_at.desc()).all()
    else:
        public = own_collections.filter(Collection.visibility == "public")
        shared_ids = (
            db.query(CollectionPermission.collection_id)
            .filter(CollectionPermission.user_id == current_user.id)
            .subquery()
        )
        shared = own_collections.filter(Collection.id.in_(shared_ids))
        visible = public.union(shared).order_by(Collection.created_at.desc()).all()

    collections_out = []
    for c in visible:
        collections_out.append(
            CollectionListOut(
                id=c.id,
                title=c.title,
                description=c.description,
                created_by=UserBriefSchema(
                    user_id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                ),
                visibility=c.visibility,
                task_type=c.task_type,
                task_source_display=c.task_source_display,
                tags=c.tags,
                created_at=c.created_at,
                updated_at=c.updated_at,
                stats=_collection_stats(db, c.id),
            )
        )

    return {
        "user": {
            "username": user.username,
            "display_name": user.display_name,
            "created_at": user.created_at,
        },
        "collections": collections_out,
    }


@router.put("/me/change-password")
def change_password(
    body: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.password_hash or not verify_password(
        body.old_password, current_user.password_hash
    ):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    current_user.password_hash = get_password_hash(body.new_password)
    db.commit()

    return {"detail": "密码修改成功"}


@router.get("/me/check")
def check_field_availability(
    field: str = Query(..., regex="^(username|email)$"),
    value: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if username or email is available (not taken by other users)"""
    if field == "username":
        existing = (
            db.query(User)
            .filter(User.username == value, User.id != current_user.id)
            .first()
        )
    else:  # email
        existing = (
            db.query(User)
            .filter(User.email == value, User.id != current_user.id)
            .first()
        )

    return {"available": existing is None}


@router.put("/me")
def update_user_profile(
    body: UpdateUserProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile (username, display_name, email)"""
    # Check username conflict
    if body.username != current_user.username:
        existing = (
            db.query(User)
            .filter(User.username == body.username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="用户名已被占用")

    # Check email conflict
    if body.email and body.email != current_user.email:
        existing = (
            db.query(User)
            .filter(User.email == body.email, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被占用")

    current_user.username = body.username
    current_user.display_name = body.display_name
    current_user.email = body.email
    db.commit()

    return {"detail": "用户信息已更新"}
