"""Configuration helpers for the ShareBib SDK and CLI."""

import json
import os
from pathlib import Path
from typing import Any

from .exceptions import ShareBibConfigError

ConfigDict = dict[str, Any]


class ConfigManager:
    """Manages configuration loading for ShareBib."""

    DEFAULT_CONFIG_PATHS = [
        Path(".sharebib") / "config.json",
        Path.home() / ".sharebib" / "config.json",
    ]
    DEFAULT_BASE_URL = "http://localhost:11550"
    DEFAULT_TIMEOUT = 30

    @classmethod
    def load_config(
        cls,
        config_path: Path | None = None,
        *,
        require_api_key: bool = True,
    ) -> ConfigDict:
        """Load configuration from file and environment variables."""
        config: ConfigDict = {
            "base_url": cls.DEFAULT_BASE_URL,
            "timeout": cls.DEFAULT_TIMEOUT,
        }

        if config_path is not None:
            file_config = cls._load_from_file(config_path)
            if file_config:
                config.update(file_config)
        else:
            for path in cls.DEFAULT_CONFIG_PATHS:
                file_config = cls._load_from_file(path)
                if file_config:
                    config.update(file_config)
                    break

        env_api_key = os.getenv("SHAREBIB_API_KEY")
        if env_api_key:
            config["api_key"] = env_api_key

        env_base_url = os.getenv("SHAREBIB_BASE_URL")
        if env_base_url:
            config["base_url"] = env_base_url

        env_timeout = os.getenv("SHAREBIB_TIMEOUT")
        if env_timeout:
            try:
                config["timeout"] = int(env_timeout)
            except ValueError as exc:
                raise ShareBibConfigError(
                    "Invalid SHAREBIB_TIMEOUT value; expected an integer"
                ) from exc

        if "base_url" in config and isinstance(config["base_url"], str):
            config["base_url"] = normalize_base_url(config["base_url"])

        timeout = config.get("timeout")
        if not isinstance(timeout, int) or timeout <= 0:
            raise ShareBibConfigError("Timeout must be a positive integer")

        if require_api_key:
            api_key = config.get("api_key")
            if not isinstance(api_key, str) or not api_key:
                raise ShareBibConfigError(
                    "API key not found. Set SHAREBIB_API_KEY or create "
                    ".sharebib/config.json or ~/.sharebib/config.json"
                )
            validate_api_key(api_key)

        return config

    @staticmethod
    def _load_from_file(path: Path) -> ConfigDict | None:
        """Load configuration from a JSON file."""
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
        except (json.JSONDecodeError, OSError) as exc:
            raise ShareBibConfigError(
                f"Failed to load config from {path}: {exc}"
            ) from exc

        if not isinstance(loaded, dict):
            raise ShareBibConfigError(
                f"Invalid config in {path}: expected a JSON object"
            )

        return loaded

    @classmethod
    def create_config_file(
        cls,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: int | None = None,
        config_path: Path | None = None,
    ) -> Path:
        """Create a local config file for ShareBib."""
        validate_api_key(api_key)

        final_timeout = timeout if timeout is not None else cls.DEFAULT_TIMEOUT
        if final_timeout <= 0:
            raise ShareBibConfigError("Timeout must be a positive integer")

        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATHS[1]

        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "api_key": api_key,
            "base_url": normalize_base_url(base_url or cls.DEFAULT_BASE_URL),
            "timeout": final_timeout,
        }

        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        if os.name != "nt":
            os.chmod(config_path, 0o600)

        return config_path


def validate_api_key(api_key: str) -> None:
    """Validate ShareBib API key format."""
    if not api_key.startswith("pc_"):
        raise ShareBibConfigError(
            "Invalid API key format. API keys should start with 'pc_'"
        )


def normalize_base_url(base_url: str) -> str:
    """Normalize a ShareBib base URL.

    The CLI/SDK expects the application root URL, not the `/api` prefix.
    If a trailing `/api` is provided, strip it to reduce configuration mistakes.
    """
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/api"):
        normalized = normalized[:-4]
    return normalized
