"""Configuration management and persistence for contrigraph."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contrigraph.utils.errors import ConfigNotFoundError, InvalidConfigError
from contrigraph.utils.platform import PlatformPaths


@dataclass
class UserConfig:
    """User configuration options."""

    username: str
    email: str = ""
    theme: str = "github-dark"
    default_year: int | None = None
    cache_ttl_hours: int = 4
    show_stats: bool = True
    compact_mode: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserConfig":
        """Build UserConfig from dictionary with validation."""
        username = data.get("username")
        if not username or not isinstance(username, str) or not username.strip():
            raise InvalidConfigError("Invalid or missing 'username' in configuration.")

        return cls(
            username=username.strip(),
            email=str(data.get("email", "")).strip(),
            theme=str(data.get("theme", "github-dark")),
            default_year=data.get("default_year"),
            cache_ttl_hours=int(data.get("cache_ttl_hours", 4)),
            show_stats=bool(data.get("show_stats", True)),
            compact_mode=bool(data.get("compact_mode", False)),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=str(data.get("updated_at", datetime.now(timezone.utc).isoformat())),
        )


class ConfigManager:
    """Handles reading, writing, and validating user configuration."""

    CONFIG_FILENAME = "config.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or PlatformPaths.get_config_dir()
        self.config_path = self.config_dir / self.CONFIG_FILENAME

    def is_configured(self) -> bool:
        """Check whether valid configuration exists on disk."""
        if not self.config_path.exists():
            return False
        try:
            self.load_config()
            return True
        except (ConfigNotFoundError, InvalidConfigError):
            return False

    def load_config(self) -> UserConfig:
        """Load and return UserConfig from file."""
        if not self.config_path.exists():
            raise ConfigNotFoundError(
                f"Configuration file not found at {self.config_path}."
            )
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UserConfig.from_dict(data)
        except json.JSONDecodeError as err:
            raise InvalidConfigError(
                f"Configuration file at {self.config_path} is corrupted: {err}",
                remediation="Run [bold green]ghcontrib setup[/bold green] to re-initialize your configuration.",
            ) from err
        except Exception as err:
            if isinstance(err, (ConfigNotFoundError, InvalidConfigError)):
                raise
            raise InvalidConfigError(
                f"Error loading configuration: {err}",
                remediation="Run [bold green]ghcontrib setup[/bold green] to repair your configuration.",
            ) from err

    def save_config(self, config: UserConfig) -> None:
        """Save UserConfig to disk atomically."""
        config.updated_at = datetime.now(timezone.utc).isoformat()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temp_file = self.config_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)
            temp_file.replace(self.config_path)
        except Exception as err:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise InvalidConfigError(f"Failed to save configuration: {err}") from err

    def update_config(self, **kwargs: Any) -> UserConfig:
        """Update specific configuration fields."""
        current = self.load_config()
        current_dict = current.to_dict()
        for key, value in kwargs.items():
            if value is not None and hasattr(current, key):
                current_dict[key] = value
        updated = UserConfig.from_dict(current_dict)
        self.save_config(updated)
        return updated

    def reset_config(self) -> None:
        """Delete local configuration file."""
        if self.config_path.exists():
            self.config_path.unlink()
