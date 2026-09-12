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


def test_null_data_payload_raises_user_not_found():
    """Verify payload with data: null raises UserNotFoundError instead of AttributeError."""
    client = GitHubClient(token="mock_valid_token")
    mock_payload = {"data": None, "errors": []}

    with patch.object(client, "_execute_graphql", return_value=mock_payload):
        with pytest.raises(UserNotFoundError):
            client.fetch_contributions("nulluser")


def test_null_data_rate_limit_returns_empty_dict():
    """Verify rate limit with data: null returns empty dict instead of AttributeError."""
    client = GitHubClient(token="mock_valid_token")
    mock_payload = {"data": None, "errors": []}

    with patch.object(client, "_execute_graphql", return_value=mock_payload):
        res = client.check_rate_limit()
        assert res == {}


# ---------------------------------------------------------------------------
# Rate-limit header parsing safety  (#6)
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int, body: str = "", headers: dict | None = None) -> MagicMock:
    """Build a minimal httpx-like response mock."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = body
    mock_resp.json.return_value = {}
    # httpx Headers allow case-insensitive lookup via .get()
    mock_headers = MagicMock()
    headers = headers or {}
    mock_headers.get = lambda key, default=None: headers.get(key, headers.get(key.lower(), default))
    mock_resp.headers = mock_headers
    return mock_resp


def test_safe_reset_time_numeric_header():
    """_safe_reset_time converts a valid Unix timestamp to a ctime string."""
    import time
    client = GitHubClient(token="tok")
    headers = MagicMock()
    headers.get = lambda key, default=None: "1999999999" if key == "x-ratelimit-reset" else default
    result = client._safe_reset_time(headers)
    assert result == time.ctime(1999999999)


def test_safe_reset_time_non_numeric_header_returns_none():
    """_safe_reset_time returns None when x-ratelimit-reset is non-numeric."""
    client = GitHubClient(token="tok")
    headers = MagicMock()
    headers.get = lambda key, default=None: "not-a-number" if key == "x-ratelimit-reset" else default
    result = client._safe_reset_time(headers)
    assert result is None


def test_safe_reset_time_empty_header_returns_none():
    """_safe_reset_time returns None when x-ratelimit-reset is empty string."""
    client = GitHubClient(token="tok")
    headers = MagicMock()
    headers.get = lambda key, default=None: "" if key == "x-ratelimit-reset" else default
    result = client._safe_reset_time(headers)
    assert result is None


def test_safe_reset_time_overflow_returns_none():
    """_safe_reset_time returns None on overflow (32-bit platform)."""
    client = GitHubClient(token="tok")
    headers = MagicMock()
    # Astronomically large value triggers OverflowError on 32-bit
    headers.get = lambda key, default=None: "99999999999999999" if key == "x-ratelimit-reset" else default
    result = client._safe_reset_time(headers)
    assert result is None


def test_safe_reset_time_retry_after_seconds():
    """_safe_reset_time uses Retry-After (seconds) when x-ratelimit-reset is absent."""
    import time as _time
    client = GitHubClient(token="tok")
    headers = MagicMock()
    headers.get = lambda key, default=None: ("60" if key == "retry-after" else default)
    before = _time.time()
    result = client._safe_reset_time(headers)
    after = _time.time()
    # Result should be a ctime string roughly 60 seconds in the future
    assert result is not None
    result_ts = _time.mktime(_time.strptime(result))
    assert before + 55 <= result_ts <= after + 65


def test_safe_reset_time_retry_after_http_date():
    """_safe_reset_time returns HTTP-date verbatim when Retry-After is not numeric."""
    client = GitHubClient(token="tok")
    headers = MagicMock()
    date_str = "Sat, 01 Jan 2028 00:00:00 GMT"
    headers.get = lambda key, default=None: (date_str if key == "retry-after" else default)
    result = client._safe_reset_time(headers)
    assert result == date_str


def test_403_rate_limit_malformed_reset_header_does_not_crash():
    """HTTP 403 with 'rate limit' body and a malformed x-ratelimit-reset must not crash."""
    client = GitHubClient(token="valid_tok")
    mock_resp = _make_mock_response(403, body="rate limit exceeded", headers={"x-ratelimit-reset": "BADVALUE"})

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(RateLimitExceededError) as exc_info:
            client.fetch_contributions("someone")
    # reset_time should be None (malformed header) but must not crash with ValueError
    assert "rate limit" in exc_info.value.message.lower()


def test_429_raises_rate_limit_exceeded():
    """HTTP 429 Too Many Requests raises RateLimitExceededError."""
    client = GitHubClient(token="valid_tok")
    import time as _time
    reset_ts = str(int(_time.time()) + 3600)
    mock_resp = _make_mock_response(429, headers={"x-ratelimit-reset": reset_ts})

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(RateLimitExceededError):
            client.fetch_contributions("someone")


def test_429_with_retry_after_raises_rate_limit_exceeded():
    """HTTP 429 with Retry-After header raises RateLimitExceededError (no x-ratelimit-reset)."""
    client = GitHubClient(token="valid_tok")
    mock_resp = _make_mock_response(429, headers={"retry-after": "120"})

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(RateLimitExceededError):
            client.fetch_contributions("someone")


def test_429_no_headers_raises_rate_limit_exceeded():
    """HTTP 429 with no rate-limit headers still raises RateLimitExceededError."""
    client = GitHubClient(token="valid_tok")
    mock_resp = _make_mock_response(429)

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(RateLimitExceededError):
            client.fetch_contributions("someone")
