"""Data models for GitHub contribution calendars, days, weeks, and stats."""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class ContributionDay:
    """Represents a single day's contribution metrics."""

    date: str  # YYYY-MM-DD
    count: int
    level: int  # 0 to 4
    weekday: int  # 0 (Sunday) to 6 (Saturday)

    @property
    def parsed_date(self) -> date:
        """Return datetime.date object."""
        return datetime.strptime(self.date, "%Y-%m-%d").date()

    @property
    def is_active(self) -> bool:
        """True if any contributions were made."""
        return self.count > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert day to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContributionDay":
        """Build ContributionDay from dictionary."""
        return cls(
            date=str(data["date"]),
            count=int(data.get("count", 0)),
            level=int(data.get("level", 0)),
            weekday=int(data.get("weekday", 0)),
        )


@dataclass
class ContributionWeek:
    """Represents a column of 7 days in the contribution calendar."""

    days: list[ContributionDay] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert week to dictionary."""
        return {"days": [d.to_dict() for d in self.days]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContributionWeek":
        """Build ContributionWeek from dictionary."""
        days = [ContributionDay.from_dict(d) for d in data.get("days", [])]
        return cls(days=days)


@dataclass
class ContributionMonth:
    """Metadata for month header placement."""

    name: str  # Jan, Feb, etc.
    year: int
    first_week_idx: int
    total_weeks: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert month metadata to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContributionMonth":
        """Build ContributionMonth from dictionary."""
        return cls(
            name=str(data["name"]),
            year=int(data.get("year", 0)),
            first_week_idx=int(data.get("first_week_idx", 0)),
            total_weeks=int(data.get("total_weeks", 1)),
        )


@dataclass
class ContributionCalendar:
    """Complete contribution calendar for a given user and period."""

    username: str
    year: int | None
    from_date: str
    to_date: str
    total_contributions: int
    total_commits: int = 0
    total_issues: int = 0
    total_prs: int = 0
    total_reviews: int = 0
    restricted_contributions: int = 0
    weeks: list[ContributionWeek] = field(default_factory=list)
    months: list[ContributionMonth] = field(default_factory=list)

    def all_days(self) -> list[ContributionDay]:
        """Return flattened list of all days in chronological order."""
        days = []
        for week in self.weeks:
            for day in week.days:
                days.append(day)
        return days

    def to_dict(self) -> dict[str, Any]:
        """Serialize calendar to dictionary."""
        return {
            "username": self.username,
            "year": self.year,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "total_contributions": self.total_contributions,
            "total_commits": self.total_commits,
            "total_issues": self.total_issues,
            "total_prs": self.total_prs,
            "total_reviews": self.total_reviews,
            "restricted_contributions": self.restricted_contributions,
            "weeks": [w.to_dict() for w in self.weeks],
            "months": [m.to_dict() for m in self.months],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContributionCalendar":
        """Deserialize calendar from dictionary."""
        weeks = [ContributionWeek.from_dict(w) for w in data.get("weeks", [])]
        months = [ContributionMonth.from_dict(m) for m in data.get("months", [])]
        return cls(
            username=str(data["username"]),
            year=data.get("year"),
            from_date=str(data.get("from_date", "")),
            to_date=str(data.get("to_date", "")),
            total_contributions=int(data.get("total_contributions", 0)),
            total_commits=int(data.get("total_commits", 0)),
            total_issues=int(data.get("total_issues", 0)),
            total_prs=int(data.get("total_prs", 0)),
            total_reviews=int(data.get("total_reviews", 0)),
            restricted_contributions=int(data.get("restricted_contributions", 0)),
            weeks=weeks,
            months=months,
        )


@dataclass
class ContributionStats:
    """Computed activity and streak statistics."""

    total_contributions: int
    current_streak: int
    longest_streak: int
    active_days: int
    total_days: int
    active_days_percentage: float
    average_per_day: float
    average_per_week: float
    max_day: str | None
    max_count: int
    most_active_weekday: str
    most_active_month: str
    total_commits: int = 0
    total_issues: int = 0
    total_prs: int = 0
    total_reviews: int = 0
    restricted_contributions: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return asdict(self)
