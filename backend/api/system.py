from pathlib import Path
import secrets
from urllib.parse import urlencode

import httpx
import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.jwt_handler import create_access_token
from auth.simple import get_password_hash
from config import config
from database import get_db
from models import User

router = APIRouter(prefix="/api/system", tags=["system"])


class SystemStatusResponse(BaseModel):
    initialized: bool
    auth_type: str
    oauth_configured: bool


class SetupRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    email: str | None = None


class SetupResponse(BaseModel):
    access_token: str
    username: str


@router.get("/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)):
    has_users = db.query(User).count() > 0
    return SystemStatusResponse(
        initialized=has_users,
        auth_type=config.auth.type,
        oauth_configured=bool(config.auth.oauth.client_id),
    )


@router.post("/setup", response_model=SetupResponse)
def setup_admin(body: SetupRequest, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(status_code=409, detail="System already initialized")

    if not body.username or not body.username.strip():
        raise HTTPException(status_code=422, detail="Username is required")
    if not body.password or len(body.password) < 6:
        raise HTTPException(
            status_code=422, detail="Password must be at least 6 characters"
        )

    user = User(
        username=body.username.strip(),
        password_hash=get_password_hash(body.password),
        display_name=body.display_name,
        email=body.email or None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Persist admin_username to config.yaml
    _update_config_admin_username(user.username)

    token = create_access_token({"sub": user.id, "username": user.username})
    return SetupResponse(access_token=token, username=user.username)


def _update_config_admin_username(username: str):
    """Write admin_username back to config.yaml so it persists across restarts."""
    import os

    config_path = Path(os.environ.get("CONFIG_PATH", "../data/config.yaml"))
    if not config_path.exists():
        return

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    data["admin_username"] = username

    # Also remove the hardcoded users list if present
    if "auth" in data and "simple" in data["auth"]:
        data["auth"]["simple"].pop("users", None)

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    # Update the in-memory config
    config.admin_username = username


# ── OAuth setup flow ──

_setup_oauth_states: dict[str, bool] = {}


@router.get("/setup/oauth/start")
def setup_oauth_start(db: Session = Depends(get_db)):
    """Start OAuth setup flow. Only available when no users exist."""
    if db.query(User).count() > 0:
        raise HTTPException(409, "System already initialized")

    oauth = config.auth.oauth
    if not oauth.client_id or not oauth.authorization_endpoint:
        raise HTTPException(400, "OAuth is not configured")

    state = secrets.token_urlsafe(32)
    _setup_oauth_states[state] = True

    params = {
        "client_id": oauth.client_id,
        "redirect_uri": oauth.redirect_uri,
        "response_type": "code",
        "scope": " ".join(oauth.scopes),
        "state": state,
    }
    url = f"{oauth.authorization_endpoint}?{urlencode(params)}"
    return {"authorization_url": url}


@router.get("/setup/oauth/callback")
def setup_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """OAuth callback for setup. Creates the first admin user from OAuth identity."""
    if db.query(User).count() > 0:
        raise HTTPException(409, "System already initialized")

    if state not in _setup_oauth_states:
        raise HTTPException(400, "Invalid OAuth state")
    _setup_oauth_states.pop(state, None)

    oauth = config.auth.oauth

    # Exchange code for access token
    resp = httpx.post(
        oauth.token_endpoint,
        data={
            "grant_type": "authorization_code",
            "client_id": oauth.client_id,
            "client_secret": oauth.client_secret,
            "code": code,
            "redirect_uri": oauth.redirect_uri,
        },
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    access_token = resp.json().get("access_token")
    if not access_token:
        raise HTTPException(400, "Failed to obtain access token from OAuth provider")

    # Get user info
    resp = httpx.get(
        oauth.userinfo_endpoint,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    resp.raise_for_status()
    userinfo = resp.json()

    oauth_sub = str(userinfo.get("sub") or userinfo.get("id") or "")
    if not oauth_sub:
        raise HTTPException(400, "OAuth provider did not return a user identifier")

    username = (
        userinfo.get("login")
        or userinfo.get("preferred_username")
        or userinfo.get("name")
        or f"user_{oauth_sub[:8]}"
    )
    email = userinfo.get("email")
    display_name = userinfo.get("name") or userinfo.get("login")

    user = User(
        username=username,
        email=email or None,
        display_name=display_name,
        oauth_provider=oauth.provider,
        oauth_sub=oauth_sub,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _update_config_admin_username(user.username)

    jwt_token = create_access_token({"sub": user.id, "username": user.username})
    return RedirectResponse(f"/?token={jwt_token}")
