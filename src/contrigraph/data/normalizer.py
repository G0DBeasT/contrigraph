"""Normalizer for GitHub GraphQL contribution calendar responses."""

from datetime import datetime
from typing import Any

from contrigraph.data.density import DensityEngine
from contrigraph.models.calendar import (
    ContributionCalendar,
    ContributionDay,
    ContributionMonth,
    ContributionWeek,
)


class ContributionNormalizer:
    """Normalizes raw GitHub GraphQL JSON payloads into structured domain models."""

    @classmethod
    def normalize_graphql_response(
        cls,
        payload: dict[str, Any],
        username: str,
        year: int | None = None,
    ) -> ContributionCalendar:
        """Parse raw GitHub GraphQL JSON into ContributionCalendar."""
        user_data = payload.get("data", {}).get("user", {})
        if not user_data:
            # Handle direct user object if wrapper omitted
            user_data = payload.get("user", {})

        collection = user_data.get("contributionsCollection", {})
        cal_data = collection.get("contributionCalendar", {})

        total_contributions = int(cal_data.get("totalContributions", 0))
        total_commits = int(collection.get("totalCommitContributions", 0))
        total_issues = int(collection.get("totalIssueContributions", 0))
        total_prs = int(collection.get("totalPullRequestContributions", 0))
        total_reviews = int(collection.get("totalPullRequestReviewContributions", 0))
        restricted_contributions = int(collection.get("restrictedContributionsCount", 0))

        raw_weeks = cal_data.get("weeks", [])
        weeks: list[ContributionWeek] = []
        all_counts: list[int] = []

        for w_idx, w_data in enumerate(raw_weeks):
            days: list[ContributionDay] = []
            for d_data in w_data.get("contributionDays", []):
                date_str = str(d_data.get("date", ""))
                count = int(d_data.get("contributionCount", 0))
                all_counts.append(count)

                # Use official GitHub level or fallback calculation
                raw_level = d_data.get("contributionLevel", "")
                if raw_level:
                    level = DensityEngine.parse_github_level(raw_level)
                else:
                    level = DensityEngine.calculate_fixed_level(count)

                weekday = int(d_data.get("weekday", 0))
                if not weekday and date_str:
                    try:
                        weekday = (datetime.strptime(date_str, "%Y-%m-%d").weekday() + 1) % 7
                    except ValueError:
                        weekday = 0

                days.append(ContributionDay(date=date_str, count=count, level=level, weekday=weekday))
            weeks.append(ContributionWeek(days=days))

        # Build month headers
        months: list[ContributionMonth] = []
        raw_months = cal_data.get("months", [])
        if raw_months:
            date_to_week: dict[str, int] = {}
            for w_idx, week in enumerate(weeks):
                for day in week.days:
                    if day.date and day.date not in date_to_week:
                        date_to_week[day.date] = w_idx

            for m_data in raw_months:
                first_day_str = str(m_data.get("firstDay", ""))
                first_week_idx: int | None = None
                if first_day_str in date_to_week:
                    first_week_idx = date_to_week[first_day_str]
                elif "-" in first_day_str:
                    for w_idx, week in enumerate(weeks):
                        if any(d.date and d.date >= first_day_str for d in week.days):
                            first_week_idx = w_idx
                            break
                if first_week_idx is None:
                    first_week_idx = int(m_data.get("firstWeekIdx", 0))

                months.append(
                    ContributionMonth(
                        name=str(m_data.get("name", "")),
                        year=int(m_data.get("year", year or 0)),
                        first_week_idx=first_week_idx,
                        total_weeks=int(m_data.get("totalWeeks", 1)),
                    )
                )
        else:
            months = cls._infer_months_from_weeks(weeks)

        from_date = ""
        to_date = ""
        if weeks and weeks[0].days:
            from_date = weeks[0].days[0].date
        if weeks and weeks[-1].days:
            to_date = weeks[-1].days[-1].date

        return ContributionCalendar(
            username=username,
            year=year,
            from_date=from_date,
            to_date=to_date,
            total_contributions=total_contributions,
            total_commits=total_commits,
            total_issues=total_issues,
            total_prs=total_prs,
            total_reviews=total_reviews,
            restricted_contributions=restricted_contributions,
            weeks=weeks,
            months=months,
        )

    @staticmethod
    def _infer_months_from_weeks(weeks: list[ContributionWeek]) -> list[ContributionMonth]:
        """Infer month boundaries from dates across weeks."""
        months: list[ContributionMonth] = []
        last_month = None
        for w_idx, week in enumerate(weeks):
            for day in week.days:
                if not day.date:
                    continue
                try:
                    dt = datetime.strptime(day.date, "%Y-%m-%d")
                    m_key = (dt.year, dt.month)
                    if m_key != last_month:
                        last_month = m_key
                        months.append(
                            ContributionMonth(
                                name=dt.strftime("%b"),
                                year=dt.year,
                                first_week_idx=w_idx,
                                total_weeks=1,
                            )
                        )
                    break
                except ValueError:
                    continue
        return months
