from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from database import get_db
from models import User
from models.api_key import ApiKey

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyOut(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    key: str  # Full key, only shown once
    key_prefix: str
    created_at: datetime


@router.get("")
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKeyOut]:
    """List all API keys for the current user."""
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [
        ApiKeyOut(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("")
def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreated:
    """Create a new API key. The full key is only returned once."""
    # Generate new key
    plain_key = ApiKey.generate_key()
    key_hash = ApiKey.hash_key(plain_key)
    key_prefix = plain_key[:11]  # "pc_" + first 8 chars

    # Create API key record
    api_key = ApiKey(
        user_id=user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,  # Return full key only once
        key_prefix=key_prefix,
        created_at=api_key.created_at,
    )


@router.delete("/{key_id}")
def delete_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an API key."""
    api_key = (
        db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    )
    if not api_key:
        raise HTTPException(404, "API key not found")

    db.delete(api_key)
    db.commit()
    return {"ok": True}


@router.patch("/{key_id}/toggle")
def toggle_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    """Toggle API key active status."""
    api_key = (
        db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    )
    if not api_key:
        raise HTTPException(404, "API key not found")

    api_key.is_active = not api_key.is_active
    db.commit()
    db.refresh(api_key)

    return ApiKeyOut(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
    )
