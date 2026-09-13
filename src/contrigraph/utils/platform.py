"""Cross-platform path resolution, security, and terminal detection utilities."""

import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PlatformPaths:
    """Provides OS-compliant configuration, cache, and data directories."""

    APP_NAME = "contrigraph"

    @classmethod
    def _safe_home(cls) -> Path:
        """Safely resolve user home directory with fallbacks for Android/Termux."""
        # 1. If HOME is unset/empty and PREFIX is set (Termux environment convention)
        if not os.environ.get("HOME", "").strip():
            if prefix := os.environ.get("PREFIX"):
                termux_home = Path(prefix.strip()).parent / "home"
                if termux_home.exists():
                    return termux_home

        # 2. Try standard Path.home() (honors mocked Path.home in tests and standard $HOME)
        try:
            return Path.home()
        except Exception:
            pass

        # 3. Check HOME environment variable if Path.home() failed
        if home := os.environ.get("HOME"):
            if home.strip():
                return Path(home.strip())

        # 4. Check Termux PREFIX convention ($PREFIX is typically /data/data/com.termux/files/usr)
        if prefix := os.environ.get("PREFIX"):
            termux_home = Path(prefix.strip()).parent / "home"
            if termux_home.exists():
                return termux_home

        # 5. Safe fallback directory for non-standard environments
        fallback = Path("/tmp")
        if fallback.exists():
            return fallback
        import tempfile

        return Path(tempfile.gettempdir())

    @classmethod
    def get_config_dir(cls) -> Path:
        """Return the user configuration directory."""
        if sys.platform == "win32":
            base = os.environ.get("APPDATA")
            path = Path(base) / cls.APP_NAME if base else cls._safe_home() / f".{cls.APP_NAME}"
        elif sys.platform == "darwin":
            path = cls._safe_home() / "Library" / "Application Support" / cls.APP_NAME
        else:
            # POSIX / Linux / Fedora (XDG Base Directory Specification)
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                path = Path(xdg_config) / cls.APP_NAME
            else:
                path = cls._safe_home() / ".config" / cls.APP_NAME

        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Return the user cache directory."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            path = Path(base) / cls.APP_NAME / "cache" if base else cls._safe_home() / f".{cls.APP_NAME}" / "cache"
        elif sys.platform == "darwin":
            path = cls._safe_home() / "Library" / "Caches" / cls.APP_NAME
        else:
            # POSIX / Linux / Fedora (XDG Base Directory Specification)
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                path = Path(xdg_cache) / cls.APP_NAME
            else:
                path = cls._safe_home() / ".cache" / cls.APP_NAME

        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_data_dir(cls) -> Path:
        """Return the user data directory."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            path = Path(base) / cls.APP_NAME / "data" if base else cls._safe_home() / f".{cls.APP_NAME}" / "data"
        elif sys.platform == "darwin":
            path = cls._safe_home() / "Library" / "Application Support" / cls.APP_NAME / "data"
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                path = Path(xdg_data) / cls.APP_NAME
            else:
                path = cls._safe_home() / ".local" / "share" / cls.APP_NAME

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


@dataclass(frozen=True)
class TerminalCapabilities:
    """Centralized descriptor of terminal environment capabilities and constraints."""

    width: int = 80
    height: int = 24
    is_tty: bool = True
    supports_unicode: bool = True
    color_depth: str = "truecolor"  # 'none', 'standard', '256', 'truecolor'

    @property
    def supports_color(self) -> bool:
        """True if the terminal supports color output (and is a TTY)."""
        return self.is_tty and self.color_depth != "none"

    @property
    def supports_truecolor(self) -> bool:
        """True if 24-bit direct RGB color output is supported."""
        return self.color_depth == "truecolor"

    @property
    def supports_256color(self) -> bool:
        """True if 256-color or 24-bit direct RGB output is supported."""
        return self.color_depth in ("256", "truecolor")

    @property
    def box_style(self) -> Any:
        """Return rich Box style adapted to Unicode capability."""
        from rich import box

        return box.ROUNDED if self.supports_unicode else box.ASCII

    @property
    def bullet_char(self) -> str:
        """Return bullet glyph ('•' for Unicode, '*' for ASCII)."""
        return "•" if self.supports_unicode else "*"

    @property
    def arrow_char(self) -> str:
        """Return arrow symbol ('→' for Unicode, '->' for ASCII)."""
        return "→" if self.supports_unicode else "->"

    @property
    def max_weeks_per_chunk(self) -> int:
        """Calculate maximum weeks visible in a single chunk with default padding."""
        usable_cols = max(6, self.width - 2)
        return max(1, (usable_cols - 4) // 2)

    def get_max_weeks_per_chunk(self, label_width: int = 4, safety_padding: int = 2) -> int:
        """Calculate maximum weeks visible in a single chunk with custom padding."""
        usable_cols = max(label_width + 2, self.width - safety_padding)
        return max(1, (usable_cols - label_width) // 2)

    def create_console(self, **kwargs: Any) -> Any:
        """Create a Rich Console configured according to these capabilities."""
        from rich.console import Console

        color_system: str | None
        if not self.is_tty or self.color_depth == "none":
            color_system = None
        elif self.color_depth == "truecolor":
            color_system = "truecolor"
        elif self.color_depth == "256":
            color_system = "256"
        elif self.color_depth == "standard":
            color_system = "standard"
        else:
            color_system = None

        params: dict[str, Any] = {
            "width": self.width,
            "height": self.height,
            "color_system": color_system,
            "force_terminal": self.is_tty,
        }
        params.update(kwargs)
        return Console(**params)

    @classmethod
    def detect(
        cls,
        stream: Any = None,
        console: Any = None,
        default_width: int = 80,
        default_height: int = 24,
    ) -> "TerminalCapabilities":
        """Detect capabilities from the environment, stream, or console."""
        if console is not None:
            stream = getattr(console, "file", sys.stdout)
            width = max(console.width, 20) if getattr(console, "width", None) is not None else None
            height = max(console.height, 1) if getattr(console, "height", None) is not None else None
            is_tty = getattr(console, "is_terminal", None)
            encoding = getattr(console, "encoding", None) or getattr(stream, "encoding", "") or ""
        else:
            stream = sys.stdout if stream is None else stream
            width = None
            height = None
            is_tty = None
            encoding = getattr(stream, "encoding", "") or ""

        if is_tty is None:
            is_tty = hasattr(stream, "isatty") and bool(stream.isatty())

        if width is None or height is None:
            try:
                cols, lines = shutil.get_terminal_size(fallback=(default_width, default_height))
                if width is None:
                    width = max(cols, 20)
                if height is None:
                    height = max(lines, 1)
            except Exception:
                if width is None:
                    width = default_width
                if height is None:
                    height = default_height

        # Unicode detection
        if stream is None or stream is sys.stdout:
            supports_uni = supports_unicode()
        else:
            supports_uni = "utf" in encoding.lower()

        # Color depth detection
        term = os.environ.get("TERM", "").lower()
        colorterm = os.environ.get("COLORTERM", "").lower()
        no_color = bool(os.environ.get("NO_COLOR"))

        if no_color:
            color_depth = "none"
        elif colorterm in ("truecolor", "24bit") or term.endswith("-direct"):
            color_depth = "truecolor"
        elif term == "dumb":
            color_depth = "none"
        elif "256color" in term or "256" in term:
            color_depth = "256"
        elif term:
            color_depth = "standard"
        else:
            color_depth = "none"

        return cls(
            width=width,
            height=height,
            is_tty=is_tty,
            supports_unicode=supports_uni,
            color_depth=color_depth,
        )


def get_terminal_width(default: int = 80) -> int:
    """Get the current terminal width in columns."""
    return TerminalCapabilities.detect(default_width=default).width


def supports_color() -> bool:
    """Check if the current terminal environment supports color output."""
    return TerminalCapabilities.detect().supports_color


def supports_truecolor() -> bool:
    """Check if terminal supports 24-bit TrueColor."""
    return TerminalCapabilities.detect().supports_truecolor


def supports_unicode() -> bool:
    """Check if the system terminal encoding supports UTF-8."""
    encoding = getattr(sys.stdout, "encoding", "") or ""
    return "utf" in encoding.lower()
