"""Statistics calculation engine for GitHub contribution calendars."""

from collections import defaultdict
from datetime import datetime

from contrigraph.models.calendar import ContributionCalendar, ContributionStats


class StatisticsEngine:
    """Computes comprehensive activity metrics, streaks, averages, and peak days."""

    WEEKDAY_NAMES = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    @classmethod
    def calculate(cls, calendar: ContributionCalendar) -> ContributionStats:
        """Compute all activity statistics from ContributionCalendar."""
        days = calendar.all_days()
        total_days = len(days)

        if total_days == 0:
            return ContributionStats(
                total_contributions=calendar.total_contributions,
                current_streak=0,
                longest_streak=0,
                active_days=0,
                total_days=0,
                active_days_percentage=0.0,
                average_per_day=0.0,
                average_per_week=0.0,
                max_day=None,
                max_count=0,
                most_active_weekday="N/A",
                most_active_month="N/A",
            )

        active_days_count = 0
        max_day = None
        max_count = 0
        weekday_sums: dict[int, int] = defaultdict(int)
        month_sums: dict[str, int] = defaultdict(int)

        current_streak = 0
        longest_streak = 0
        running_streak = 0

        for day in days:
            count = day.count
            if count > 0:
                active_days_count += 1
                running_streak += 1
                if running_streak > longest_streak:
                    longest_streak = running_streak
                if count > max_count:
                    max_count = count
                    max_day = day.date
            else:
                running_streak = 0

            weekday_sums[day.weekday] += count

            if day.date:
                try:
                    dt = datetime.strptime(day.date, "%Y-%m-%d")
                    month_sums[dt.strftime("%B")] += count
                except ValueError:
                    pass

        # Calculate current streak ending at the end of the timeline
        curr_streak = 0
        now_year = datetime.now().year
        is_past_year = calendar.year is not None and calendar.year < now_year

        if not is_past_year and days:
            check_days = list(reversed(days))
            # If the last day (today) has 0 contributions, check if yesterday was active
            if check_days[0].count == 0 and len(check_days) > 1:
                check_days = check_days[1:]

            for day in check_days:
                if day.count > 0:
                    curr_streak += 1
                else:
                    break

        current_streak = curr_streak

        active_percentage = round((active_days_count / total_days) * 100, 1) if total_days > 0 else 0.0
        avg_day = round(calendar.total_contributions / total_days, 2) if total_days > 0 else 0.0
        avg_week = round((calendar.total_contributions / total_days) * 7, 2) if total_days > 0 else 0.0

        # Most active weekday
        most_active_weekday = "N/A"
        if weekday_sums:
            best_wday_idx = max(weekday_sums, key=lambda k: weekday_sums[k])
            if 0 <= best_wday_idx < len(cls.WEEKDAY_NAMES):
                most_active_weekday = cls.WEEKDAY_NAMES[best_wday_idx]

        # Most active month
        most_active_month = "N/A"
        if month_sums:
            most_active_month = max(month_sums, key=lambda k: month_sums[k])

        return ContributionStats(
            total_contributions=calendar.total_contributions,
            current_streak=current_streak,
            longest_streak=longest_streak,
            active_days=active_days_count,
            total_days=total_days,
            active_days_percentage=active_percentage,
            average_per_day=avg_day,
            average_per_week=avg_week,
            max_day=max_day,
            max_count=max_count,
            most_active_weekday=most_active_weekday,
            most_active_month=most_active_month,
            total_commits=calendar.total_commits,
            total_issues=calendar.total_issues,
            total_prs=calendar.total_prs,
            total_reviews=calendar.total_reviews,
            restricted_contributions=calendar.restricted_contributions,
        )
