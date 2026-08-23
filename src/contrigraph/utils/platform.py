"""Cross-platform path resolution, security, and terminal detection utilities."""

import os
import shutil
import stat
import sys
from pathlib import Path


class PlatformPaths:
    """Provides OS-compliant configuration, cache, and data directories."""

    APP_NAME = "contrigraph"

    @classmethod
    def get_config_dir(cls) -> Path:
        """Return the user configuration directory."""
        if sys.platform == "win32":
            base = os.environ.get("APPDATA")
            path = Path(base) / cls.APP_NAME if base else Path.home() / f".{cls.APP_NAME}"
        elif sys.platform == "darwin":
            path = Path.home() / "Library" / "Application Support" / cls.APP_NAME
        else:
            # POSIX / Linux / Fedora (XDG Base Directory Specification)
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                path = Path(xdg_config) / cls.APP_NAME
            else:
                path = Path.home() / ".config" / cls.APP_NAME

        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Return the user cache directory."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            path = Path(base) / cls.APP_NAME / "cache" if base else Path.home() / f".{cls.APP_NAME}" / "cache"
        elif sys.platform == "darwin":
            path = Path.home() / "Library" / "Caches" / cls.APP_NAME
        else:
            # POSIX / Linux / Fedora (XDG Base Directory Specification)
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                path = Path(xdg_cache) / cls.APP_NAME
            else:
                path = Path.home() / ".cache" / cls.APP_NAME

        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_data_dir(cls) -> Path:
        """Return the user data directory."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            path = Path(base) / cls.APP_NAME / "data" if base else Path.home() / f".{cls.APP_NAME}" / "data"
        elif sys.platform == "darwin":
            path = Path.home() / "Library" / "Application Support" / cls.APP_NAME / "data"
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                path = Path(xdg_data) / cls.APP_NAME
            else:
                path = Path.home() / ".local" / "share" / cls.APP_NAME

        path.mkdir(parents=True, exist_ok=True)
        return path


def set_secure_file_permissions(file_path: Path) -> None:
    """Set strict read/write permissions for current user only (0600 on POSIX)."""
    if not file_path.exists():
        return
    try:
        if os.name == "posix":
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        # Ignore on platforms or filesystems that do not support POSIX chmod
        pass


def get_terminal_width(default: int = 80) -> int:
    """Get the current terminal width in columns."""
    try:
        cols, _ = shutil.get_terminal_size(fallback=(default, 24))
        return max(cols, 40)
    except Exception:
        return default


def supports_color() -> bool:
    """Check if the current terminal environment supports color output."""
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    return True


def supports_truecolor() -> bool:
    """Check if terminal supports 24-bit TrueColor."""
    colorterm = os.environ.get("COLORTERM", "").lower()
    return colorterm in ("truecolor", "24bit") or "xterm-256color" in os.environ.get("TERM", "").lower()


def supports_unicode() -> bool:
    """Check if the system terminal encoding supports UTF-8."""
    encoding = getattr(sys.stdout, "encoding", "") or ""
    return "utf" in encoding.lower()
