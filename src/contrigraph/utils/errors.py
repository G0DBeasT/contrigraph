"""Domain exceptions for contrigraph."""

class ContrigraphError(Exception):
    """Base exception for all contrigraph runtime errors."""

    def __init__(self, message: str, remediation: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.remediation = remediation

    def __str__(self) -> str:
        if self.remediation:
            return f"{self.message}\n\n[bold yellow]Fix:[/bold yellow] {self.remediation}"
        return self.message


# --- Configuration Exceptions ---

class ConfigError(ContrigraphError):
    """Base error for configuration issues."""


class ConfigNotFoundError(ConfigError):
    """Raised when configuration has not been initialized."""

    def __init__(self, message: str = "Configuration not found.") -> None:
        super().__init__(
            message=message,
            remediation="Run [bold green]ghcontrib setup[/bold green] to initialize your settings.",
        )


class InvalidConfigError(ConfigError):
    """Raised when configuration file is malformed or has invalid values."""


# --- Authentication Exceptions ---

class AuthError(ContrigraphError):
    """Base error for authentication issues."""


class MissingTokenError(AuthError):
    """Raised when no GitHub authentication token is configured or found."""

    def __init__(self, message: str = "GitHub authentication token not found.") -> None:
        super().__init__(
            message=message,
            remediation="Run [bold green]ghcontrib auth login[/bold green] or set the [bold cyan]GITHUB_TOKEN[/bold cyan] environment variable.",
        )


class InvalidTokenError(AuthError):
    """Raised when GitHub token is invalid, expired, or rejected."""

    def __init__(self, message: str = "GitHub token is invalid or expired.") -> None:
        super().__init__(
            message=message,
            remediation="Run [bold green]ghcontrib auth login[/bold green] to re-authenticate with a valid Personal Access Token.",
        )


# --- API & Network Exceptions ---

class APIError(ContrigraphError):
    """Base error for GitHub API failures."""


class UserNotFoundError(APIError):
    """Raised when the specified GitHub user does not exist."""

    def __init__(self, username: str) -> None:
        super().__init__(
            message=f"GitHub user '{username}' was not found.",
            remediation="Check the username spelling or run [bold green]ghcontrib setup[/bold green] to update your default user.",
        )


class RateLimitExceededError(APIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_time: str | None = None) -> None:
        msg = "GitHub API rate limit exceeded."
        if reset_time:
            msg += f" Rate limit resets at {reset_time}."
        super().__init__(
            message=msg,
            remediation="Authenticate with a personal access token via [bold green]ghcontrib auth login[/bold green] for 5,000 requests/hour.",
        )


class NetworkError(APIError):
    """Raised when network connection to GitHub API fails."""

    def __init__(self, message: str = "Unable to connect to GitHub API.") -> None:
        super().__init__(
            message=message,
            remediation="Check your internet connection, DNS settings, or GitHub status at https://www.githubstatus.com/.",
        )


class GitHubServerError(APIError):
    """Raised when GitHub responds with 5xx server errors."""

    def __init__(self, status_code: int, details: str = "") -> None:
        super().__init__(
            message=f"GitHub API server error ({status_code}): {details}".strip(),
            remediation="GitHub is experiencing issues. Please try again in a few moments or run [bold green]ghcontrib doctor[/bold green].",
        )


# --- Rendering Exceptions ---

class RenderError(ContrigraphError):
    """Raised when terminal rendering fails."""
