"""GitHub authentication and credential management for contrigraph."""

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from contrigraph.utils.errors import AuthError, InvalidTokenError, MissingTokenError
from contrigraph.utils.platform import PlatformPaths, set_secure_file_permissions


@dataclass
class AuthCredentials:
    """Stored authentication credentials."""

    token: str
    token_type: str = "Bearer"
    username: str = ""
    scopes: list[str] = field(default_factory=list)
    authenticated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthCredentials":
        """Build AuthCredentials from dictionary."""
        token = data.get("token")
        if not token or not isinstance(token, str):
            raise InvalidTokenError("Authentication token is missing or malformed.")
        return cls(
            token=token.strip(),
            token_type=str(data.get("token_type", "Bearer")),
            username=str(data.get("username", "")),
            scopes=list(data.get("scopes", [])),
            authenticated_at=str(data.get("authenticated_at", datetime.now(timezone.utc).isoformat())),
        )


@dataclass
class AuthStatus:
    """Authentication status report."""

    is_authenticated: bool
    source: str  # "file", "env:GITHUB_TOKEN", "env:GH_TOKEN", "cli:gh", or "none"
    username: str = ""
    scopes: list[str] = field(default_factory=list)
    masked_token: str = ""
    message: str = ""


class AuthManager:
    """Manages token retrieval, storage, validation, and logout."""

    AUTH_FILENAME = "auth.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or PlatformPaths.get_config_dir()
        self.auth_path = self.config_dir / self.AUTH_FILENAME

    @staticmethod
    def mask_token(token: str) -> str:
        """Return masked token string for secure display (e.g. ghp_***1234)."""
        if not token:
            return ""
        if len(token) <= 8:
            return "******"
        return f"{token[:4]}...{token[-4:]}"

    def get_token(self) -> str | None:
        """Resolve token from environment, stored file, or GitHub CLI."""
        # 1. Check GITHUB_TOKEN or GH_TOKEN environment variables
        env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if env_token and env_token.strip():
            return env_token.strip()

        # 2. Check stored auth.json file
        if self.auth_path.exists():
            try:
                with open(self.auth_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                creds = AuthCredentials.from_dict(data)
                if creds.token:
                    return creds.token
            except Exception:
                pass

        # 3. Check GitHub CLI (gh) if available
        gh_token = self._get_gh_cli_token()
        if gh_token:
            return gh_token

        return None

    def require_token(self) -> str:
        """Return resolved token or raise MissingTokenError."""
        token = self.get_token()
        if not token:
            raise MissingTokenError()
        return token

    def _get_gh_cli_token(self) -> str | None:
        """Query token from GitHub CLI `gh auth token` if installed."""
        if not shutil.which("gh"):
            return None
        try:
            res = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return None

    def validate_token(self, token: str) -> tuple[bool, str, list[str]]:
        """Validate token against GitHub REST API and retrieve username and scopes."""
        clean_token = token.strip()
        if not clean_token:
            return False, "", []

        headers = {
            "Authorization": f"Bearer {clean_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "contrigraph/0.1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get("https://api.github.com/user", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    login = data.get("login", "")
                    scopes_header = res.headers.get("x-oauth-scopes", "")
                    scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
                    return True, login, scopes
                return False, "", []
        except Exception:
            return False, "", []

    def login(self, token: str, validate: bool = True) -> AuthCredentials:
        """Save token with secure permissions after optional validation."""
        clean_token = token.strip()
        if not clean_token:
            raise InvalidTokenError("Token cannot be empty.")

        username = ""
        scopes: list[str] = []

        if validate:
            is_valid, user_login, token_scopes = self.validate_token(clean_token)
            if not is_valid:
                raise InvalidTokenError(
                    "GitHub rejected the provided token. Ensure the token is valid and active."
                )
            username = user_login
            scopes = token_scopes

        creds = AuthCredentials(token=clean_token, username=username, scopes=scopes)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temp_file = self.auth_path.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(creds.to_dict(), f, indent=2)
            set_secure_file_permissions(temp_file)
            temp_file.replace(self.auth_path)
            set_secure_file_permissions(self.auth_path)
            return creds
        except Exception as err:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise AuthError(f"Failed to save authentication credentials: {err}") from err

    def logout(self) -> None:
        """Remove stored credentials file."""
        if self.auth_path.exists():
            self.auth_path.unlink()

    def get_auth_status(self) -> AuthStatus:
        """Provide detailed status of current authentication configuration."""
        if os.environ.get("GITHUB_TOKEN"):
            token = os.environ["GITHUB_TOKEN"].strip()
            return AuthStatus(
                is_authenticated=True,
                source="env:GITHUB_TOKEN",
                masked_token=self.mask_token(token),
                message="Authenticated via GITHUB_TOKEN environment variable",
            )
        if os.environ.get("GH_TOKEN"):
            token = os.environ["GH_TOKEN"].strip()
            return AuthStatus(
                is_authenticated=True,
                source="env:GH_TOKEN",
                masked_token=self.mask_token(token),
                message="Authenticated via GH_TOKEN environment variable",
            )
        if self.auth_path.exists():
            try:
                with open(self.auth_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                creds = AuthCredentials.from_dict(data)
                return AuthStatus(
                    is_authenticated=True,
                    source="file",
                    username=creds.username,
                    scopes=creds.scopes,
                    masked_token=self.mask_token(creds.token),
                    message=f"Authenticated locally as @{creds.username}" if creds.username else "Authenticated locally",
                )
            except Exception:
                pass

        gh_token = self._get_gh_cli_token()
        if gh_token:
            return AuthStatus(
                is_authenticated=True,
                source="cli:gh",
                masked_token=self.mask_token(gh_token),
                message="Authenticated via GitHub CLI (gh auth token)",
            )

        return AuthStatus(
            is_authenticated=False,
            source="none",
            message="Not authenticated. Run 'ghcontrib auth login' to authenticate.",
        )
