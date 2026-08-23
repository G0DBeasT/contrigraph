"""Unit tests for platform and path resolution utilities."""

import os
import sys
from pathlib import Path

from contrigraph.utils.platform import (
    PlatformPaths,
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
    assert get_terminal_width() >= 40

    monkeypatch.setenv("NO_COLOR", "1")
    assert not supports_color()

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("COLORTERM", "truecolor")
    assert supports_truecolor()
