"""Unit tests for statistics and streak calculation engine."""

from contrigraph.data.normalizer import ContributionNormalizer
from contrigraph.models.calendar import ContributionCalendar, ContributionDay, ContributionWeek
from contrigraph.statistics.engine import StatisticsEngine
from tests.fixtures.mock_data import make_mock_calendar_payload


def test_statistics_calculation():
    """Verify statistics calculations across full calendar."""
    payload = make_mock_calendar_payload(username="octocat", total_contributions=487)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "octocat", 2026)

    stats = StatisticsEngine.calculate(cal)
    assert stats.total_contributions == 487
    assert stats.total_days > 300
    assert stats.active_days > 0
    assert stats.average_per_day > 0
    assert stats.longest_streak >= stats.current_streak
    assert stats.max_count > 0
    assert stats.most_active_weekday in StatisticsEngine.WEEKDAY_NAMES


def test_streak_calculation_precise():
    """Verify streak detection on known pattern of active and inactive days."""
    # Day 1: 0, Day 2: 5, Day 3: 10, Day 4: 0, Day 5: 3, Day 6: 4, Day 7: 8
    # Longest streak = 3 (days 5,6,7), Current streak = 3
    days = [
        ContributionDay(date="2026-03-01", count=0, level=0, weekday=0),
        ContributionDay(date="2026-03-02", count=5, level=2, weekday=1),
        ContributionDay(date="2026-03-03", count=10, level=3, weekday=2),
        ContributionDay(date="2026-03-04", count=0, level=0, weekday=3),
        ContributionDay(date="2026-03-05", count=3, level=2, weekday=4),
        ContributionDay(date="2026-03-06", count=4, level=2, weekday=5),
        ContributionDay(date="2026-03-07", count=8, level=3, weekday=6),
    ]
    cal = ContributionCalendar(
        username="streakuser",
        year=2026,
        from_date="2026-03-01",
        to_date="2026-03-07",
        total_contributions=30,
        weeks=[ContributionWeek(days=days)],
    )

    stats = StatisticsEngine.calculate(cal)
    assert stats.total_contributions == 30
    assert stats.active_days == 5
    assert stats.total_days == 7
    assert stats.longest_streak == 3
    assert stats.current_streak == 3
    assert stats.max_count == 10
    assert stats.max_day == "2026-03-03"


def test_empty_calendar_statistics():
    """Verify clean stats for zero-day calendar."""
    cal = ContributionCalendar(
        username="emptyuser",
        year=2026,
        from_date="",
        to_date="",
        total_contributions=0,
        weeks=[],
    )
    stats = StatisticsEngine.calculate(cal)
    assert stats.total_contributions == 0
    assert stats.current_streak == 0
    assert stats.longest_streak == 0
    assert stats.active_days == 0
