"""GitHub GraphQL API client for contribution data fetching."""

import time
from typing import Any

import httpx

from contrigraph.data.normalizer import ContributionNormalizer
from contrigraph.models.calendar import ContributionCalendar
from contrigraph.utils.errors import (
    APIError,
    GitHubServerError,
    InvalidTokenError,
    NetworkError,
    RateLimitExceededError,
    UserNotFoundError,
)

GRAPHQL_QUERY = """
query GetUserContributions($username: String!, $from: DateTime, $to: DateTime) {
  user(login: $username) {
    name
    login
    avatarUrl
    createdAt
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
            weekday
          }
        }
        months {
          name
          year
          firstDay
          totalWeeks
        }
      }
    }
  }
}
"""

RATE_LIMIT_QUERY = """
query GetRateLimit {
  rateLimit {
    limit
    cost
    remaining
    resetAt
  }
}
"""


class GitHubClient:
    """Client for querying GitHub GraphQL API."""

    API_URL = "https://api.github.com/graphql"
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 15.0

    def __init__(self, token: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.token = token
        self.timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        """Construct request headers with authorization."""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "contrigraph/0.1.0",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _execute_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute GraphQL query with retries and structured error translation."""
        if not self.token:
            raise InvalidTokenError(
                "GitHub GraphQL API requires authentication. No token was provided."
            )

        headers = self._get_headers()
        body = {"query": query, "variables": variables or {}}

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(self.API_URL, headers=headers, json=body)

                # Status code checks
                if response.status_code == 401:
                    raise InvalidTokenError()

                if response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        reset_header = response.headers.get("x-ratelimit-reset")
                        reset_str = time.ctime(int(reset_header)) if reset_header else None
                        raise RateLimitExceededError(reset_time=reset_str)
                    raise InvalidTokenError("Access forbidden (403). Verify token permissions.")

                if response.status_code in (500, 502, 503, 504):
                    if attempt < self.MAX_RETRIES:
                        time.sleep(0.5 * (2 ** (attempt - 1)))
                        continue
                    raise GitHubServerError(response.status_code, response.text[:200])

                if response.status_code != 200:
                    raise APIError(f"GitHub API returned unexpected status {response.status_code}: {response.text[:200]}")

                # Parse JSON response
                try:
                    payload = response.json()
                except Exception as err:
                    raise APIError(f"Malformed JSON response from GitHub API: {err}") from err

                # Handle GraphQL-level errors
                if "errors" in payload and payload["errors"]:
                    errors = payload["errors"]
                    for err in errors:
                        err_type = str(err.get("type", "")).upper()
                        err_msg = str(err.get("message", ""))

                        if err_type in ("NOT_FOUND", "COULD_NOT_RESOLVE_TO_USER") or "could not resolve to a user" in err_msg.lower():
                            username = (variables or {}).get("username", "Unknown")
                            raise UserNotFoundError(username)
                        if "rate limit" in err_msg.lower() or err_type == "RATE_LIMITED":
                            raise RateLimitExceededError()
                        if "bad credentials" in err_msg.lower() or err_type == "FORBIDDEN":
                            raise InvalidTokenError(err_msg)

                    raise APIError(f"GitHub GraphQL error: {errors[0].get('message', 'Unknown error')}")

                return payload

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as net_err:
                last_error = net_err
                if attempt < self.MAX_RETRIES:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise NetworkError(f"Network connection failed: {net_err}") from net_err

        if last_error:
            raise NetworkError(f"Network request failed after {self.MAX_RETRIES} attempts: {last_error}")
        raise NetworkError("API request failed.")

    def fetch_contributions(
        self,
        username: str,
        year: int | None = None,
    ) -> ContributionCalendar:
        """Fetch raw contribution calendar and normalize into domain model."""
        clean_user = username.strip()
        if not clean_user:
            raise UserNotFoundError("")

        variables: dict[str, Any] = {"username": clean_user}
        if year is not None:
            variables["from"] = f"{year}-01-01T00:00:00Z"
            variables["to"] = f"{year}-12-31T23:59:59Z"

        payload = self._execute_graphql(GRAPHQL_QUERY, variables)
        user_node = (payload.get("data") or {}).get("user")
        if not user_node:
            raise UserNotFoundError(clean_user)

        return ContributionNormalizer.normalize_graphql_response(
            payload=payload,
            username=clean_user,
            year=year,
        )

    def check_rate_limit(self) -> dict[str, Any]:
        """Query current GraphQL API rate limit information."""
        payload = self._execute_graphql(RATE_LIMIT_QUERY)
        return (payload.get("data") or {}).get("rateLimit") or {}
