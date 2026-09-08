"""Integration test for complete CLI workflow (setup, auth, show, stats, doctor, refresh)."""

from unittest.mock import patch

from contrigraph.cli.main import main
from tests.fixtures.mock_data import make_mock_calendar_payload, make_mock_rate_limit_payload


def test_full_cli_lifecycle(mock_env, monkeypatch):
    """Simulate complete user journey through CLI subcommands."""
    # 1. Setup user
    res = main(["setup", "--user", "integration_user", "--email", "dev@example.com", "--theme", "emerald"])
    assert res == 0

    # 2. Auth login (mock remote validate)
    with patch("contrigraph.auth.manager.AuthManager.validate_token", return_value=(True, "integration_user", ["read:user"])):
        res = main(["auth", "login", "--token", "ghp_mock_test_token_1234567890"])
        assert res == 0

    # 3. Auth status
    res = main(["auth", "status"])
    assert res == 0

    # 4. Config show & update
    res = main(["config", "show"])
    assert res == 0
    res = main(["config", "set", "theme", "halloween"])
    assert res == 0

    # 5. Show contributions (mock GraphQL)
    mock_cal_data = make_mock_calendar_payload("integration_user", total_contributions=512)
    mock_rate_data = make_mock_rate_limit_payload()

    with patch("contrigraph.api.client.GitHubClient._execute_graphql") as mock_exec:
        mock_exec.side_effect = [mock_cal_data, mock_rate_data, mock_cal_data]

        # First run (fetches and caches)
        res = main(["show"])
        assert res == 0

        # Run stats only
        res = main(["stats"])
        assert res == 0

        # Run doctor diagnostics
        res = main(["doctor"])
        assert res == 0

        # Run refresh
        res = main(["refresh"])
        assert res == 0

    # 6. Auth logout
    res = main(["auth", "logout"])
    assert res == 0
