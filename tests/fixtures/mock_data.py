"""Mock data fixtures for GitHub API tests."""

from datetime import datetime, timedelta


def make_mock_calendar_payload(
    username: str = "octocat",
    total_contributions: int = 487,
    start_date: str = "2026-01-01",
    num_weeks: int = 52,
) -> dict:
    """Generate realistic GraphQL contribution calendar payload."""
    weeks = []
    base_dt = datetime.strptime(start_date, "%Y-%m-%d")

    for w in range(num_weeks):
        days = []
        for d in range(7):
            cur_dt = base_dt + timedelta(days=(w * 7) + d)
            count = (w + d) % 15 if (w + d) % 3 != 0 else 0
            if count == 0:
                level = "NONE"
            elif count <= 2:
                level = "FIRST_QUARTILE"
            elif count <= 5:
                level = "SECOND_QUARTILE"
            elif count <= 10:
                level = "THIRD_QUARTILE"
            else:
                level = "FOURTH_QUARTILE"

            days.append(
                {
                    "date": cur_dt.strftime("%Y-%m-%d"),
                    "contributionCount": count,
                    "contributionLevel": level,
                    "weekday": d,
                }
            )
        weeks.append({"contributionDays": days})

    months = [
        {"name": "Jan", "year": 2026, "firstDay": "2026-01-01", "totalWeeks": 4, "firstWeekIdx": 0},
        {"name": "Feb", "year": 2026, "firstDay": "2026-02-01", "totalWeeks": 4, "firstWeekIdx": 4},
        {"name": "Mar", "year": 2026, "firstDay": "2026-03-01", "totalWeeks": 5, "firstWeekIdx": 8},
        {"name": "Apr", "year": 2026, "firstDay": "2026-04-01", "totalWeeks": 4, "firstWeekIdx": 13},
        {"name": "May", "year": 2026, "firstDay": "2026-05-01", "totalWeeks": 4, "firstWeekIdx": 17},
        {"name": "Jun", "year": 2026, "firstDay": "2026-06-01", "totalWeeks": 5, "firstWeekIdx": 21},
        {"name": "Jul", "year": 2026, "firstDay": "2026-07-01", "totalWeeks": 4, "firstWeekIdx": 26},
        {"name": "Aug", "year": 2026, "firstDay": "2026-08-01", "totalWeeks": 5, "firstWeekIdx": 30},
        {"name": "Sep", "year": 2026, "firstDay": "2026-09-01", "totalWeeks": 4, "firstWeekIdx": 35},
        {"name": "Oct", "year": 2026, "firstDay": "2026-10-01", "totalWeeks": 4, "firstWeekIdx": 39},
        {"name": "Nov", "year": 2026, "firstDay": "2026-11-01", "totalWeeks": 5, "firstWeekIdx": 43},
        {"name": "Dec", "year": 2026, "firstDay": "2026-12-01", "totalWeeks": 4, "firstWeekIdx": 48},
    ]

    return {
        "data": {
            "user": {
                "name": "The Octocat",
                "login": username,
                "avatarUrl": "https://avatars.githubusercontent.com/u/583231",
                "createdAt": "2011-01-25T18:44:36Z",
                "contributionsCollection": {
                    "totalCommitContributions": 312,
                    "totalIssueContributions": 45,
                    "totalPullRequestContributions": 80,
                    "totalPullRequestReviewContributions": 50,
                    "restrictedContributionsCount": 0,
                    "contributionCalendar": {
                        "totalContributions": total_contributions,
                        "weeks": weeks,
                        "months": months,
                    },
                },
            }
        }
    }


def make_mock_rate_limit_payload(remaining: int = 4999, limit: int = 5000) -> dict:
    """Generate rate limit query response."""
    return {
        "data": {
            "rateLimit": {
                "limit": limit,
                "cost": 1,
                "remaining": remaining,
                "resetAt": "2026-08-23T18:00:00Z",
            }
        }
    }
