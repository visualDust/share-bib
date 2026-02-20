import os
import secrets
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class JWTConfig(BaseModel):
    secret_key: str = ""
    algorithm: str = "HS256"
    expire_days: int = 7


class SimpleAuthConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")


class OAuthConfig(BaseModel):
    provider: str = "generic"
    client_id: str = ""
    client_secret: str = ""
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    userinfo_endpoint: str = ""
    redirect_uri: str = ""
    scopes: list[str] = ["openid", "profile", "email"]
    admin_group: str = "admins"


class AuthConfig(BaseModel):
    type: str = "simple"
    simple: SimpleAuthConfig = SimpleAuthConfig()
    oauth: OAuthConfig = OAuthConfig()
    jwt: JWTConfig = JWTConfig()


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    auth: AuthConfig = AuthConfig()
    admin_username: str = ""
    data_dir: str = "../data"
    branding: str = "ShareBib"


def _get_config_path() -> Path:
    return Path(os.environ.get("CONFIG_PATH", "../data/config.yaml"))


def load_config() -> AppConfig:
    # 1. Start with env-var based config
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    auth_type = os.environ.get("AUTH_TYPE", "simple")
    admin_user = os.environ.get("ADMIN_USERNAME", "")
    data_dir = os.environ.get("DATA_DIR", "../data")

    cfg = AppConfig(
        auth=AuthConfig(
            type=auth_type,
            jwt=JWTConfig(secret_key=jwt_secret),
        ),
        admin_username=admin_user,
        data_dir=data_dir,
    )

    # 2. If config.yaml exists, overlay its values
    config_path = _get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        cfg = AppConfig(**data)

    # 3. Env vars override config.yaml for key settings
    if os.environ.get("JWT_SECRET_KEY"):
        cfg.auth.jwt.secret_key = os.environ["JWT_SECRET_KEY"]
    if os.environ.get("AUTH_TYPE"):
        cfg.auth.type = os.environ["AUTH_TYPE"]
    if os.environ.get("ADMIN_USERNAME"):
        cfg.admin_username = os.environ["ADMIN_USERNAME"]
    if os.environ.get("DATA_DIR"):
        cfg.data_dir = os.environ["DATA_DIR"]

    # 4. Auto-generate JWT secret if still empty
    if not cfg.auth.jwt.secret_key:
        cfg.auth.jwt.secret_key = secrets.token_hex(32)
        _persist_jwt_secret(cfg.auth.jwt.secret_key)

    return cfg


def _persist_jwt_secret(secret: str):
    """Save auto-generated JWT secret to config.yaml so it survives restarts."""
    config_path = _get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

    data.setdefault("auth", {}).setdefault("jwt", {})["secret_key"] = secret

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


config = load_config()
