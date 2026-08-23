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
