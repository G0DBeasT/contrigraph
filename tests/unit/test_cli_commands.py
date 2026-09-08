"""Unit tests covering all CLI command switches and error handling branches."""

from unittest.mock import MagicMock, patch
import pytest

from contrigraph.cli.doctor import Doctor
from contrigraph.cli.main import build_parser, main
from contrigraph.utils.errors import (
    APIError,
    AuthError,
    ConfigError,
    ContrigraphError,
    NetworkError,
    RateLimitExceededError,
    UserNotFoundError,
)
from tests.fixtures.mock_data import make_mock_calendar_payload, make_mock_rate_limit_payload


def test_cli_parser_help():
    """Verify parser generation and subcommand registration."""
    parser = build_parser()
    assert parser.prog == "ghcontrib"


def test_cli_version(capsys):
    """Verify version command output."""
    res = main(["version"])
    assert res == 0
    out, _ = capsys.readouterr()
    assert "0.1.0" in out


def test_cli_setup_non_interactive(mock_env):
    """Test setup with explicit arguments."""
    res = main(["setup", "--user", "alice", "--email", "alice@example.com", "--theme", "github-light"])
    assert res == 0

    res = main(["config", "show"])
    assert res == 0


def test_cli_config_set_and_reset(mock_env):
    """Test config set and reset flows."""
    main(["setup", "--user", "bob", "--email", "bob@example.com"])

    # Invalid theme
    res = main(["config", "set", "theme", "nonexistent_theme"])
    assert res == 1

    # Valid theme
    res = main(["config", "set", "theme", "halloween"])
    assert res == 0

    # Reset
    res = main(["config", "reset"])
    assert res == 0

    # Show on empty
    res = main(["config", "show"])
    assert res == 0


def test_cli_show_formats_and_flags(mock_env):
    """Test show with flags: --no-color, --ascii, --compact, --no-stats, --format."""
    main(["setup", "--user", "charlie"])

    mock_cal = make_mock_calendar_payload("charlie", 120)
    with patch("contrigraph.api.client.GitHubClient._execute_graphql", return_value=mock_cal):
        # ASCII mode
        res = main(["show", "--ascii"])
        assert res == 0

        # No color & compact
        res = main(["show", "--no-color", "--compact"])
        assert res == 0

        # No stats
        res = main(["show", "--no-stats"])
        assert res == 0

        # JSON format
        res = main(["show", "--format", "json"])
        assert res == 0

        # CSV format
        res = main(["show", "--format", "csv"])
        assert res == 0


def test_cli_error_presentation(mock_env, capsys):
    """Verify clean error formatting on domain exceptions."""
    main(["setup", "--user", "erroruser"])

    with patch("contrigraph.api.client.GitHubClient._execute_graphql", side_effect=UserNotFoundError("erroruser")):
        res = main(["show"])
        assert res == 1

    with patch("contrigraph.api.client.GitHubClient._execute_graphql", side_effect=NetworkError("DNS failure")):
        res = main(["show"])
        assert res == 1


def test_cli_stale_cache_fallback_on_network_error(mock_env, capsys):
    """Verify CLI falls back to stale cached data when network fails and displays warning."""
    import json
    from contrigraph.cache.manager import CacheManager
    from contrigraph.data.normalizer import ContributionNormalizer

    main(["setup", "--user", "offlineuser"])

    # Seed cache with expired data
    mgr = CacheManager()
    payload = make_mock_calendar_payload("offlineuser", 99)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "offlineuser", None)
    mgr.set(cal)

    cache_file = mgr._get_cache_file("offlineuser", None)
    with open(cache_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["fetched_at"] = "2020-01-01T00:00:00+00:00"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # When network fails, show should fall back to stale cache and exit 0
    with patch("contrigraph.api.client.GitHubClient._execute_graphql", side_effect=NetworkError("Connection refused")):
        res = main(["show"])
        assert res == 0
        out, _ = capsys.readouterr()
        assert "Displaying cached data" in out



def test_doctor_failure_states(mock_env):
    """Verify doctor command reports issues gracefully when unauthenticated or unconfigured."""
    doc = Doctor()
    # Not configured, not authenticated
    success = doc.run_diagnostics()
    assert not success


def test_cli_auth_login_token_stdin(mock_env):
    """Verify auth login --token-stdin reads token from standard input."""
    with patch("sys.stdin.read", return_value="ghp_stdin_token_1234567890\n"), \
         patch("contrigraph.auth.manager.AuthManager.login") as mock_login:
        from contrigraph.auth.manager import AuthCredentials
        mock_login.return_value = AuthCredentials(token="ghp_stdin_token_1234567890", username="testuser")
        res = main(["auth", "login", "--token-stdin", "--no-validate"])
        assert res == 0
        mock_login.assert_called_once_with("ghp_stdin_token_1234567890", validate=False)


def test_cli_auth_login_token_stdin_empty(mock_env):
    """Verify auth login --token-stdin with empty input fails cleanly."""
    with patch("sys.stdin.read", return_value="   \n"):
        res = main(["auth", "login", "--token-stdin"])
        assert res == 1


def test_cli_auth_login_token_arg_warning(mock_env):
    """Verify passing --token shows warning and proceeds."""
    with patch("contrigraph.auth.manager.AuthManager.login") as mock_login:
        from contrigraph.auth.manager import AuthCredentials
        mock_login.return_value = AuthCredentials(token="ghp_arg_token_1234567890", username="testuser")
        res = main(["auth", "login", "--token", "ghp_arg_token_1234567890", "--no-validate"])
        assert res == 0
        mock_login.assert_called_once_with("ghp_arg_token_1234567890", validate=False)

