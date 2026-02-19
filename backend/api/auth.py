import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from auth.jwt_handler import create_access_token
from auth.simple import verify_password
from config import config
from database import get_db
from models import User
from schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory state store for OAuth CSRF protection
_oauth_states: dict[str, bool] = {}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if (
        user is None
        or not user.password_hash
        or not verify_password(req.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token({"sub": user.id, "username": user.username})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    out = UserOut.model_validate(current_user)
    # Check both database field and config for backward compatibility
    out.is_admin = (
        current_user.is_admin or current_user.username == config.admin_username
    )
    return out


# ── OAuth login flow ──


@router.get("/oauth/start")
def oauth_start():
    """Return the OAuth authorization URL for the configured provider."""
    oauth = config.auth.oauth
    if not oauth.client_id or not oauth.authorization_endpoint:
        raise HTTPException(400, "OAuth is not configured")

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = True

    params = {
        "client_id": oauth.client_id,
        "redirect_uri": oauth.redirect_uri,
        "response_type": "code",
        "scope": " ".join(oauth.scopes),
        "state": state,
    }
    url = f"{oauth.authorization_endpoint}?{urlencode(params)}"
    return {"authorization_url": url}


@router.get("/oauth/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Exchange authorization code for user info, find existing user, return JWT via redirect."""
    if state not in _oauth_states:
        raise HTTPException(400, "Invalid OAuth state")
    _oauth_states.pop(state, None)

    oauth = config.auth.oauth
    token_data = _exchange_code(oauth, code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(400, "Failed to obtain access token from OAuth provider")

    userinfo = _get_userinfo(oauth, access_token)
    oauth_sub = str(userinfo.get("sub") or userinfo.get("id") or "")
    if not oauth_sub:
        raise HTTPException(400, "OAuth provider did not return a user identifier")

    # Check if user is in admin group
    groups = userinfo.get("groups", [])
    is_admin = oauth.admin_group in groups if isinstance(groups, list) else False

    user = (
        db.query(User)
        .filter(
            User.oauth_provider == oauth.provider,
            User.oauth_sub == oauth_sub,
        )
        .first()
    )

    if user is None:
        # Auto-create user on first OAuth login
        username = (
            userinfo.get("preferred_username") or userinfo.get("email") or oauth_sub
        )
        email = userinfo.get("email")
        display_name = userinfo.get("name") or username

        # Check if username already exists, if so try to link by email
        existing_user = db.query(User).filter(User.username == username).first()
        if (
            existing_user
            and existing_user.email == email
            and not existing_user.oauth_provider
        ):
            # Link existing user to OAuth
            existing_user.oauth_provider = oauth.provider
            existing_user.oauth_sub = oauth_sub
            existing_user.is_admin = is_admin
            if not existing_user.display_name:
                existing_user.display_name = display_name
            db.commit()
            db.refresh(existing_user)
            user = existing_user
        else:
            # Create new user with unique username if needed
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User(
                username=username,
                email=email,
                display_name=display_name,
                oauth_provider=oauth.provider,
                oauth_sub=oauth_sub,
                is_admin=is_admin,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # Update existing user's admin status from OAuth groups
        if user.is_admin != is_admin:
            user.is_admin = is_admin
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(403, "Account is disabled")

    jwt_token = create_access_token({"sub": user.id, "username": user.username})
    return RedirectResponse(f"/?token={jwt_token}")


def _exchange_code(oauth, code: str) -> dict:
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
    return resp.json()


def _get_userinfo(oauth, access_token: str) -> dict:
    resp = httpx.get(
        oauth.userinfo_endpoint,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    resp.raise_for_status()
    return resp.json()
