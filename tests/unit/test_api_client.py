"""Unit tests for GitHub GraphQL client."""

from unittest.mock import MagicMock, patch
import pytest

from contrigraph.api.client import GitHubClient
from contrigraph.utils.errors import (
    InvalidTokenError,
    RateLimitExceededError,
    UserNotFoundError,
)
from tests.fixtures.mock_data import make_mock_calendar_payload, make_mock_rate_limit_payload


def test_missing_token_raises():
    """Client without token raises InvalidTokenError on execute."""
    client = GitHubClient(token=None)
    with pytest.raises(InvalidTokenError):
        client.fetch_contributions("octocat")


def test_successful_fetch():
    """Verify mock GraphQL response parsing."""
    client = GitHubClient(token="mock_valid_token")
    mock_payload = make_mock_calendar_payload("octocat", 487)

    with patch.object(client, "_execute_graphql", return_value=mock_payload):
        cal = client.fetch_contributions("octocat", 2026)
        assert cal.username == "octocat"
        assert cal.total_contributions == 487


def test_user_not_found_raises():
    """GraphQL errors containing user not found translate to UserNotFoundError."""
    client = GitHubClient(token="mock_valid_token")
    mock_response = {
        "errors": [{"type": "NOT_FOUND", "message": "Could not resolve to a User with the login of 'nonexistentuser'."}]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_post.return_value = mock_resp

        with pytest.raises(UserNotFoundError):
            client.fetch_contributions("nonexistentuser")


def test_rate_limit_check():
    """Verify rate limit querying."""
    client = GitHubClient(token="mock_valid_token")
    mock_payload = make_mock_rate_limit_payload(remaining=4990, limit=5000)

    with patch.object(client, "_execute_graphql", return_value=mock_payload):
        res = client.check_rate_limit()
        assert res["remaining"] == 4990
        assert res["limit"] == 5000
