"""Unit tests for platform and path resolution utilities."""

import os
import sys
from pathlib import Path

from contrigraph.utils.platform import (
    PlatformPaths,
    TerminalCapabilities,
    get_terminal_width,
    set_secure_file_permissions,
    supports_color,
    supports_truecolor,
    supports_unicode,
)


def test_platform_paths_linux(monkeypatch, temp_dir):
    """Verify XDG directory resolution on Linux."""
    cfg_dir = temp_dir / "custom_config"
    cache_dir = temp_dir / "custom_cache"
    data_dir = temp_dir / "custom_data"

    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg_dir))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_dir))
    monkeypatch.setattr(sys, "platform", "linux")

    assert PlatformPaths.get_config_dir() == cfg_dir / "contrigraph"
    assert PlatformPaths.get_cache_dir() == cache_dir / "contrigraph"
    assert PlatformPaths.get_data_dir() == data_dir / "contrigraph"


def test_platform_paths_macos(monkeypatch, temp_dir):
    """Verify macOS directory resolution."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: temp_dir)
    monkeypatch.setattr(sys, "platform", "darwin")

    assert PlatformPaths.get_config_dir() == temp_dir / "Library" / "Application Support" / "contrigraph"
    assert PlatformPaths.get_cache_dir() == temp_dir / "Library" / "Caches" / "contrigraph"


def test_platform_paths_windows(monkeypatch, temp_dir):
    """Verify Windows directory resolution."""
    appdata = temp_dir / "AppData" / "Roaming"
    localappdata = temp_dir / "AppData" / "Local"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))
    monkeypatch.setattr(sys, "platform", "win32")

    assert PlatformPaths.get_config_dir() == appdata / "contrigraph"
    assert PlatformPaths.get_cache_dir() == localappdata / "contrigraph" / "cache"


def test_secure_file_permissions(temp_dir):
    """Verify 0600 file permission setting."""
    test_file = temp_dir / "secret.txt"
    test_file.write_text("token-secret")
    set_secure_file_permissions(test_file)
    if os.name == "posix":
        mode = test_file.stat().st_mode & 0o777
        assert mode == 0o600


def test_terminal_detection(monkeypatch):
    """Verify terminal width and feature detection."""
    assert get_terminal_width() >= 20

    # Verify narrow terminal size clamping
    import shutil
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback: os.terminal_size((15, 24)))
    assert get_terminal_width() == 20

    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback: os.terminal_size((45, 24)))
    assert get_terminal_width() == 45

    monkeypatch.setenv("NO_COLOR", "1")
    assert not supports_color()

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLORTERM", "truecolor")
    assert supports_truecolor()


def test_supports_truecolor(monkeypatch):
    """Verify distinction between 256-color and 24-bit TrueColor."""
    # When COLORTERM is truecolor or 24bit, TrueColor is supported
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.delenv("TERM", raising=False)
    assert supports_truecolor()

    monkeypatch.setenv("COLORTERM", "24bit")
    assert supports_truecolor()

    monkeypatch.setenv("COLORTERM", "TrueColor")
    assert supports_truecolor()

    # When COLORTERM is unset, xterm-256color must NOT be treated as TrueColor
    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert not supports_truecolor()

    # Direct-color terminals ending with -direct support TrueColor
    monkeypatch.setenv("TERM", "xterm-direct")
    assert supports_truecolor()

    monkeypatch.setenv("TERM", "alacritty-direct")
    assert supports_truecolor()

    # Standard terminals without COLORTERM do not support TrueColor
    monkeypatch.setenv("TERM", "xterm")
    assert not supports_truecolor()

    monkeypatch.setenv("TERM", "screen")
    assert not supports_truecolor()

    monkeypatch.delenv("TERM", raising=False)
    assert not supports_truecolor()


# ---------------------------------------------------------------------------
# TerminalCapabilities centralized abstraction (#5)
# ---------------------------------------------------------------------------

def test_terminal_capabilities_properties():
    """Verify helper properties of TerminalCapabilities."""
    from rich import box

    # Unicode + TrueColor + TTY
    caps = TerminalCapabilities(
        width=80,
        height=24,
        is_tty=True,
        supports_unicode=True,
        color_depth="truecolor",
    )
    assert caps.supports_color is True
    assert caps.supports_truecolor is True
    assert caps.supports_256color is True
    assert caps.bullet_char == "•"
    assert caps.arrow_char == "→"
    assert caps.box_style == box.ROUNDED
    assert caps.max_weeks_per_chunk == 37
    assert caps.get_max_weeks_per_chunk(label_width=4, safety_padding=2) == 37

    # Non-Unicode + monochrome
    caps_ascii = TerminalCapabilities(
        width=40,
        height=10,
        is_tty=True,
        supports_unicode=False,
        color_depth="none",
    )
    assert caps_ascii.supports_color is False
    assert caps_ascii.supports_truecolor is False
    assert caps_ascii.supports_256color is False
    assert caps_ascii.bullet_char == "*"
    assert caps_ascii.arrow_char == "->"
    assert caps_ascii.box_style == box.ASCII
    assert caps_ascii.max_weeks_per_chunk == 17


def test_terminal_capabilities_piped_output_downgrade():
    """Piped/redirected output (is_tty=False) disables color by default."""
    caps = TerminalCapabilities(
        width=80,
        height=24,
        is_tty=False,
        supports_unicode=True,
        color_depth="truecolor",
    )
    assert caps.is_tty is False
    assert caps.supports_color is False
    assert caps.supports_truecolor is True  # Environment itself is TrueColor capable


def test_terminal_capabilities_detect_color_depth(monkeypatch):
    """Test environment-based color_depth detection with mocked stream."""
    class MockStream:
        def __init__(self, tty=True, encoding="utf-8"):
            self._tty = tty
            self.encoding = encoding

        def isatty(self):
            return self._tty

    stream = MockStream(tty=True)

    # COLORTERM=truecolor -> truecolor
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("TERM", "xterm")
    caps = TerminalCapabilities.detect(stream=stream)
    assert caps.color_depth == "truecolor"
    assert caps.supports_truecolor is True
    assert caps.supports_color is True

    # COLORTERM unset, TERM=xterm-256color -> 256
    monkeypatch.delenv("COLORTERM", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    caps = TerminalCapabilities.detect(stream=stream)
    assert caps.color_depth == "256"
    assert caps.supports_truecolor is False
    assert caps.supports_256color is True
    assert caps.supports_color is True

    # TERM ending in -direct -> truecolor
    monkeypatch.setenv("TERM", "xterm-direct")
    caps = TerminalCapabilities.detect(stream=stream)
    assert caps.color_depth == "truecolor"
    assert caps.supports_truecolor is True

    # TERM=vt100 -> standard
    monkeypatch.setenv("TERM", "vt100")
    caps = TerminalCapabilities.detect(stream=stream)
    assert caps.color_depth == "standard"
    assert caps.supports_color is True
    assert caps.supports_256color is False

    # TERM=dumb -> none
    monkeypatch.setenv("TERM", "dumb")
    caps = TerminalCapabilities.detect(stream=stream)
    assert caps.color_depth == "none"
    assert caps.supports_color is False

    # NO_COLOR=1 -> none regardless of TERM or COLORTERM
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLORTERM", "truecolor")
    monkeypatch.setenv("TERM", "xterm-256color")
    caps = TerminalCapabilities.detect(stream=stream)
    assert caps.color_depth == "none"
    assert caps.supports_color is False


def test_terminal_capabilities_detect_encoding():
    """Test detection of UTF-8 vs non-UTF-8 stream encoding."""
    class MockStream:
        def __init__(self, encoding):
            self.encoding = encoding

        def isatty(self):
            return True

    utf_stream = MockStream("UTF-8")
    assert TerminalCapabilities.detect(stream=utf_stream).supports_unicode is True

    ascii_stream = MockStream("ascii")
    assert TerminalCapabilities.detect(stream=ascii_stream).supports_unicode is False

    latin1_stream = MockStream("ISO-8859-1")
    assert TerminalCapabilities.detect(stream=latin1_stream).supports_unicode is False


def test_terminal_capabilities_create_console():
    """Verify create_console builds a Rich Console configured to match capabilities."""
    caps_tc = TerminalCapabilities(width=100, height=30, is_tty=True, color_depth="truecolor")
    console_tc = caps_tc.create_console()
    assert console_tc.width == 100
    assert console_tc.height == 30
    assert console_tc.color_system == "truecolor"

    caps_256 = TerminalCapabilities(width=80, height=24, is_tty=True, color_depth="256")
    console_256 = caps_256.create_console()
    assert console_256.color_system == "256"

    caps_none = TerminalCapabilities(width=80, height=24, is_tty=False, color_depth="none")
    console_none = caps_none.create_console()
    assert console_none.color_system is None
