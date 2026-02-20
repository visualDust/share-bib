from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from database import get_db
from models import User
from models.user_setting import UserSetting

router = APIRouter(prefix="/api/user-settings", tags=["user-settings"])

# Keys that are allowed to be stored (whitelist for security)
ALLOWED_KEYS = {
    "semantic_scholar_api_key",
    "openreview_token",
}

# Keys that should be masked when returned to the frontend
SECRET_KEYS = {
    "semantic_scholar_api_key",
    "openreview_token",
}


class SettingUpdate(BaseModel):
    key: str
    value: str


class SettingOut(BaseModel):
    key: str
    value: str
    is_set: bool


def _mask_value(key: str, value: str) -> str:
    if key in SECRET_KEYS and value:
        if len(value) <= 8:
            return "••••••••"
        return value[:4] + "•" * (len(value) - 8) + value[-4:]
    return value


@router.get("")
def list_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all user settings (secrets are masked)."""
    rows = db.query(UserSetting).filter(UserSetting.user_id == user.id).all()
    existing = {r.key: r.value for r in rows}

    result = []
    for key in sorted(ALLOWED_KEYS):
        val = existing.get(key, "")
        result.append(
            SettingOut(
                key=key,
                value=_mask_value(key, val) if val else "",
                is_set=bool(val),
            )
        )
    return result


@router.put("")
def update_setting(
    body: SettingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a user setting."""
    if body.key not in ALLOWED_KEYS:
        raise HTTPException(400, f"Unknown setting key: {body.key}")

    row = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == user.id, UserSetting.key == body.key)
        .first()
    )

    if row:
        row.value = body.value
    else:
        row = UserSetting(user_id=user.id, key=body.key, value=body.value)
        db.add(row)

    db.commit()
    return {"ok": True}


@router.delete("/{key}")
def delete_setting(
    key: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a user setting."""
    if key not in ALLOWED_KEYS:
        raise HTTPException(400, f"Unknown setting key: {key}")

    row = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == user.id, UserSetting.key == key)
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}
