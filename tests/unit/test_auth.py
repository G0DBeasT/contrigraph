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


# ---------------------------------------------------------------------------
# Token resolution precedence and whitespace handling (#7)
# ---------------------------------------------------------------------------

def test_gh_token_takes_precedence_over_github_token(monkeypatch, temp_dir):
    """GH_TOKEN must win over GITHUB_TOKEN (GitHub CLI standard)."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)
    monkeypatch.setattr(AuthManager, "_get_gh_cli_token", lambda self: None)

    monkeypatch.setenv("GH_TOKEN", "ghp_ghtok_valid")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_githubtok_valid")

    assert mgr.get_token() == "ghp_ghtok_valid"

    status = mgr.get_auth_status()
    assert status.is_authenticated
    assert status.source == "env:GH_TOKEN"


def test_whitespace_github_token_falls_back_to_gh_token(monkeypatch, temp_dir):
    """Whitespace-only GITHUB_TOKEN must not prevent GH_TOKEN from being used."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)
    monkeypatch.setattr(AuthManager, "_get_gh_cli_token", lambda self: None)

    monkeypatch.setenv("GITHUB_TOKEN", "   ")   # whitespace-only
    monkeypatch.setenv("GH_TOKEN", "ghp_fallback_valid")

    assert mgr.get_token() == "ghp_fallback_valid"

    status = mgr.get_auth_status()
    assert status.is_authenticated
    assert status.source == "env:GH_TOKEN"


def test_whitespace_only_env_tokens_not_authenticated(monkeypatch, temp_dir):
    """Whitespace-only values for both env vars yield unauthenticated (no file / no CLI)."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)
    monkeypatch.setattr(AuthManager, "_get_gh_cli_token", lambda self: None)

    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    monkeypatch.setenv("GH_TOKEN", "   ")

    assert mgr.get_token() is None

    status = mgr.get_auth_status()
    assert not status.is_authenticated
    assert status.source == "none"


def test_get_token_strips_whitespace_from_env(monkeypatch, temp_dir):
    """Leading/trailing whitespace in a valid token value is stripped."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)
    monkeypatch.setattr(AuthManager, "_get_gh_cli_token", lambda self: None)

    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "  ghp_padded_token  ")

    assert mgr.get_token() == "ghp_padded_token"


def test_get_auth_status_consistent_with_get_token(monkeypatch, temp_dir):
    """get_auth_status() and get_token() agree on the same source and value."""
    auth_dir = temp_dir / "auth"
    mgr = AuthManager(config_dir=auth_dir)
    monkeypatch.setattr(AuthManager, "_get_gh_cli_token", lambda self: None)

    # Both absent
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert mgr.get_token() is None
    assert not mgr.get_auth_status().is_authenticated

    # Only GITHUB_TOKEN set
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_only_github")
    assert mgr.get_token() == "ghp_only_github"
    status = mgr.get_auth_status()
    assert status.is_authenticated
    assert status.source == "env:GITHUB_TOKEN"

    # GH_TOKEN also set — GH_TOKEN must win
    monkeypatch.setenv("GH_TOKEN", "ghp_only_gh")
    assert mgr.get_token() == "ghp_only_gh"
    status = mgr.get_auth_status()
    assert status.is_authenticated
    assert status.source == "env:GH_TOKEN"
