"""Unit tests for configuration manager and settings."""

import pytest

from contrigraph.config.manager import ConfigManager, UserConfig
from contrigraph.utils.errors import ConfigNotFoundError, InvalidConfigError


def test_config_crud(temp_dir):
    """Test creating, reading, updating, and resetting configuration."""
    cfg_dir = temp_dir / "config"
    mgr = ConfigManager(config_dir=cfg_dir)

    assert not mgr.is_configured()
    with pytest.raises(ConfigNotFoundError):
        mgr.load_config()

    # Save
    cfg = UserConfig(username="testuser", email="test@example.com", theme="emerald")
    mgr.save_config(cfg)
    assert mgr.is_configured()

    # Load
    loaded = mgr.load_config()
    assert loaded.username == "testuser"
    assert loaded.email == "test@example.com"
    assert loaded.theme == "emerald"
    assert loaded.cache_ttl_hours == 4

    # Update
    updated = mgr.update_config(theme="halloween", cache_ttl_hours=8)
    assert updated.theme == "halloween"
    assert updated.cache_ttl_hours == 8

    # Reset
    mgr.reset_config()
    assert not mgr.is_configured()


def test_corrupted_config(temp_dir):
    """Verify handling of invalid or corrupted JSON in config file."""
    cfg_dir = temp_dir / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    corrupted_file = cfg_dir / "config.json"
    corrupted_file.write_text("{invalid json...")

    mgr = ConfigManager(config_dir=cfg_dir)
    assert not mgr.is_configured()
    with pytest.raises(InvalidConfigError):
        mgr.load_config()


def test_missing_username_validation():
    """Verify error on empty username."""
    with pytest.raises(InvalidConfigError):
        UserConfig.from_dict({"username": "   "})
