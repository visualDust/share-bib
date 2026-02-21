from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from auth.jwt_handler import decode_access_token
from config import config
from database import get_db
from models import User
from models.api_key import ApiKey

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username != config.admin_username:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Get current user if authenticated, otherwise return None.
    Used for endpoints that support both authenticated and unauthenticated access.
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None

    return user


async def get_user_from_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate user via API key from X-API-Key header.
    Used for programmatic access to the API.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Find API key by prefix (first 8 chars)
    if not x_api_key.startswith("pc_") or len(x_api_key) < 11:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    prefix = x_api_key[:11]  # "pc_" + first 8 chars of random part
    api_keys = db.query(ApiKey).filter(ApiKey.key_prefix == prefix).all()

    # Verify the full key against stored hashes
    user = None
    matched_key = None
    for api_key in api_keys:
        if api_key.is_active and ApiKey.verify_key(x_api_key, api_key.key_hash):
            matched_key = api_key
            user = db.query(User).filter(User.id == api_key.user_id).first()
            break

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    # Update last_used_at
    if matched_key:
        matched_key.last_used_at = datetime.now(timezone.utc)
        db.commit()

    return user
