"""Unit tests for contribution normalizer and calendar domain model."""

from contrigraph.data.normalizer import ContributionNormalizer
from contrigraph.models.calendar import ContributionCalendar
from tests.fixtures.mock_data import make_mock_calendar_payload


def test_normalize_graphql_response():
    """Verify conversion from raw GraphQL JSON to ContributionCalendar model."""
    payload = make_mock_calendar_payload(username="octocat", total_contributions=487)
    calendar = ContributionNormalizer.normalize_graphql_response(
        payload=payload,
        username="octocat",
        year=2026,
    )

    assert calendar.username == "octocat"
    assert calendar.year == 2026
    assert calendar.total_contributions == 487
    assert calendar.total_commits == 312
    assert calendar.total_prs == 80
    assert len(calendar.weeks) == 52
    assert len(calendar.months) == 12

    all_days = calendar.all_days()
    assert len(all_days) > 0
    assert all_days[0].date == "2026-01-01"


def test_calendar_serialization():
    """Verify round-trip serialization of ContributionCalendar."""
    payload = make_mock_calendar_payload(username="testdev", total_contributions=100)
    cal1 = ContributionNormalizer.normalize_graphql_response(payload, "testdev", 2026)

    data = cal1.to_dict()
    cal2 = ContributionCalendar.from_dict(data)

    assert cal2.username == cal1.username
    assert cal2.total_contributions == cal1.total_contributions
    assert len(cal2.weeks) == len(cal1.weeks)
    assert len(cal2.all_days()) == len(cal1.all_days())


def test_normalize_month_headers_first_week_idx():
    """Verify first_week_idx spans across 0..52 weeks and does not use month numbers 1..12."""
    payload = make_mock_calendar_payload(username="octocat", total_contributions=200)
    calendar = ContributionNormalizer.normalize_graphql_response(payload, "octocat", 2026)

    month_indices = [m.first_week_idx for m in calendar.months]
    month_names = [m.name for m in calendar.months]

    assert len(month_indices) == 12
    assert month_names == ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    assert month_indices == [0, 4, 8, 12, 17, 21, 25, 30, 34, 39, 43, 47]
    # Ensure December is at week 47, NOT week 12
    assert calendar.months[-1].name == "Dec"
    assert calendar.months[-1].first_week_idx == 47


def test_normalize_graphql_months_without_first_week_idx_field():
    """Verify standard GitHub GraphQL responses without synthetic firstWeekIdx field resolve correctly."""
    payload = make_mock_calendar_payload(username="octocat", total_contributions=200)
    # Strip firstWeekIdx from raw months to simulate real GitHub GraphQL response
    for m in payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["months"]:
        m.pop("firstWeekIdx", None)

    calendar = ContributionNormalizer.normalize_graphql_response(payload, "octocat", 2026)
    month_indices = [m.first_week_idx for m in calendar.months]
    assert month_indices == [0, 4, 8, 12, 17, 21, 25, 30, 34, 39, 43, 47]


def test_normalize_graphql_null_data_payload():
    """Verify normalize_graphql_response safely handles {'data': None} without raising AttributeError."""
    payload = {"data": None}
    calendar = ContributionNormalizer.normalize_graphql_response(payload, "nulluser", 2026)
    assert calendar.username == "nulluser"
    assert calendar.total_contributions == 0
    assert len(calendar.weeks) == 0
    assert len(calendar.months) == 0


