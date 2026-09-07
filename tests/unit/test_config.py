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


def test_boolean_config_string_coercion():
    """Verify boolean config fields parse string values properly."""
    # "false" string representations
    for false_val in ("false", "FALSE", "0", "no", "off", "disable", "disabled", False):
        cfg = UserConfig.from_dict({"username": "user", "show_stats": false_val, "compact_mode": False})
        assert cfg.show_stats is False, f"Failed for {false_val}"

    # "true" string representations
    for true_val in ("true", "TRUE", "1", "yes", "on", "enable", "enabled", True):
        cfg = UserConfig.from_dict({"username": "user", "show_stats": True, "compact_mode": true_val})
        assert cfg.compact_mode is True, f"Failed for {true_val}"


def test_config_manager_update_boolean_from_cli_string(temp_dir):
    """Verify ConfigManager.update_config handles CLI string values for booleans."""
    cfg_dir = temp_dir / "config"
    mgr = ConfigManager(config_dir=cfg_dir)

    mgr.save_config(UserConfig(username="user", show_stats=True, compact_mode=False))

    # Disable show_stats via string "false"
    mgr.update_config(show_stats="false")
    loaded = mgr.load_config()
    assert loaded.show_stats is False

    # Enable compact_mode via string "true"
    mgr.update_config(compact_mode="true")
    loaded = mgr.load_config()
    assert loaded.compact_mode is True

