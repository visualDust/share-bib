from sqlalchemy.orm import Session

from models import Collection, CollectionPermission


def check_collection_permission(
    db: Session,
    user_id: str,
    collection_id: str,
    required_permission: str,
) -> bool:
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        return False

    # Creator has all permissions
    if collection.created_by == user_id:
        return True

    # Public collections are viewable by all
    if collection.visibility == "public" and required_permission == "view":
        return True

    # Check explicit permissions
    perm = (
        db.query(CollectionPermission)
        .filter(
            CollectionPermission.collection_id == collection_id,
            CollectionPermission.user_id == user_id,
        )
        .first()
    )
    if not perm:
        return False

    if required_permission == "view":
        return perm.permission in ("view", "edit")
    elif required_permission == "edit":
        return perm.permission == "edit"

    return False
