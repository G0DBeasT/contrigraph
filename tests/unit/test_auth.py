"""Unit tests for authentication and credential manager."""

import pytest

from contrigraph.auth.manager import AuthCredentials, AuthManager
from contrigraph.utils.errors import InvalidTokenError, MissingTokenError


def test_auth_crud_and_masking(temp_dir, monkeypatch):
    """Test token saving, masking, retrieval, and logout."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(AuthManager, "_get_gh_cli_token", lambda self: None)
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)

    # Empty
    assert mgr.get_token() is None
    with pytest.raises(MissingTokenError):
        mgr.require_token()

    # Login without remote validate
    token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    creds = mgr.login(token=token, validate=False)
    assert creds.token == token
    assert mgr.get_token() == token
    assert mgr.require_token() == token

    # Masking
    masked = AuthManager.mask_token(token)
    assert masked.startswith("ghp_")
    assert masked.endswith("wxyz")
    assert "..." in masked

    # Logout
    mgr.logout()
    assert mgr.get_token() is None


def test_auth_from_env(monkeypatch, temp_dir):
    """Verify fallback to environment variables."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token_val_123456")
    assert mgr.get_token() == "ghp_env_token_val_123456"

    status = mgr.get_auth_status()
    assert status.is_authenticated
    assert status.source == "env:GITHUB_TOKEN"


def test_auth_validate_mock(temp_dir, monkeypatch):
    """Verify token validation flow with mocked response."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)

    def mock_validate(self, token):
        if token == "valid_token":
            return True, "testuser", ["read:user"]
        return False, "", []

    monkeypatch.setattr(AuthManager, "validate_token", mock_validate)

    creds = mgr.login("valid_token", validate=True)
    assert creds.username == "testuser"
    assert "read:user" in creds.scopes

    with pytest.raises(InvalidTokenError):
        mgr.login("invalid_token", validate=True)
