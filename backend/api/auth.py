import secrets
from urllib.parse import urlencode

import httpx
from auth.deps import get_current_user
from auth.jwt_handler import create_access_token
from auth.simple import verify_password
from config import config
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from models import User
from schemas import LoginRequest, TokenResponse, UserOut
from services.user_identity import (
    normalize_display_name,
    normalize_oauth_email,
    normalize_oauth_username,
    suffix_oauth_username,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory state store for OAuth CSRF protection
_oauth_states: dict[str, bool] = {}


def _sync_oauth_admin(user: User, provider_grants_admin: bool) -> None:
    """Sync only OAuth-derived roles; never demote setup/manual admins."""
    if provider_grants_admin:
        if not user.is_admin:
            user.is_admin = True
            user.admin_source = "oauth"
            user.token_version += 1
        return
    if user.is_admin and user.admin_source == "oauth":
        user.is_admin = False
        user.admin_source = None
        user.token_version += 1


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

    token = create_access_token(
        {"sub": user.id, "username": user.username, "ver": user.token_version}
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    out = UserOut.model_validate(current_user)
    out.is_admin = current_user.is_admin
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

    # First try to find user by oauth_sub
    user = (
        db.query(User)
        .filter(
            User.oauth_provider == oauth.provider,
            User.oauth_sub == oauth_sub,
        )
        .first()
    )

    # If not found by oauth_sub, try to find by email (for migration after OAuth provider changes)
    email = normalize_oauth_email(userinfo.get("email"))
    email_verified = userinfo.get("email_verified") is True
    if user is None and email and email_verified:
        user = (
            db.query(User)
            .filter(
                User.email == email,
                User.oauth_provider.isnot(None),
            )
            .first()
        )
        if user:
            # Update oauth_sub and oauth_provider for this user (migration case)
            user.oauth_sub = oauth_sub
            user.oauth_provider = oauth.provider
            db.commit()
            db.refresh(user)

    if user is None:
        # Auto-create user on first OAuth login
        username_source = (
            userinfo.get("preferred_username") or userinfo.get("email") or oauth_sub
        )
        username = normalize_oauth_username(username_source, oauth_sub)
        display_name = normalize_display_name(userinfo.get("name"), username)

        # Check if username already exists, if so try to link by email
        existing_user = db.query(User).filter(User.username == username).first()
        if (
            existing_user
            and existing_user.email == email
            and not existing_user.oauth_provider
            and email_verified
        ):
            # Link existing user to OAuth
            existing_user.oauth_provider = oauth.provider
            existing_user.oauth_sub = oauth_sub
            _sync_oauth_admin(existing_user, is_admin)
            if not existing_user.display_name:
                existing_user.display_name = display_name
            db.commit()
            db.refresh(existing_user)
            user = existing_user
        else:
            email_owner = (
                db.query(User).filter(User.email == email).first() if email else None
            )
            if email_owner:
                raise HTTPException(
                    403,
                    "OAuth email is already in use and was not verified for account linking",
                )
            # Create new user with unique username if needed
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = suffix_oauth_username(base_username, counter)
                counter += 1

            user = User(
                username=username,
                email=email,
                display_name=display_name,
                oauth_provider=oauth.provider,
                oauth_sub=oauth_sub,
                is_admin=is_admin,
                admin_source="oauth" if is_admin else None,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        previous_role = (user.is_admin, user.admin_source, user.token_version)
        _sync_oauth_admin(user, is_admin)
        if previous_role != (user.is_admin, user.admin_source, user.token_version):
            db.commit()
            db.refresh(user)

    if not user.is_active:
        raise HTTPException(403, "Account is disabled")

    jwt_token = create_access_token(
        {"sub": user.id, "username": user.username, "ver": user.token_version}
    )
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
