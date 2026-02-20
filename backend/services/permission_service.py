from sqlalchemy.orm import Session

from models import Collection, CollectionPermission


def check_collection_permission(
    db: Session,
    user_id: str | None,
    collection_id: str,
    required_permission: str,
) -> bool:
    """
    Check if a user has permission to access a collection.

    Args:
        user_id: User ID, or None for unauthenticated users
        collection_id: Collection ID
        required_permission: "view" or "edit"

    Returns:
        True if the user has the required permission
    """
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        return False

    # Creator has all permissions
    if user_id and collection.created_by == user_id:
        return True

    # Unauthenticated users can only view public collections
    if user_id is None:
        if required_permission == "view":
            return collection.visibility in ("public", "public_editable")
        return False

    # Authenticated users: check default permissions based on visibility
    if collection.visibility == "public" and required_permission == "view":
        return True
    if collection.visibility == "public_editable":
        # Authenticated users can view and edit public_editable collections
        return True

    # Check explicit permissions (for private/shared collections, or to override defaults)
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
