"""Terminal rendering engine for GitHub contribution calendars."""

import csv
import io
import json
import sys
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from contrigraph.models.calendar import ContributionCalendar, ContributionStats, ContributionWeek
from contrigraph.rendering.themes import ColorTheme, get_theme
from contrigraph.statistics.engine import StatisticsEngine
from contrigraph.utils.platform import get_terminal_width


class CalendarRenderer:
    """Renders contribution calendars to terminal or export formats."""

    # Weekday display labels (0=Sunday, 1=Monday, ..., 6=Saturday)
    ROW_LABELS = ["   ", "Mon", "   ", "Wed", "   ", "Fri", "   "]

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render(
        self,
        calendar: ContributionCalendar,
        stats: ContributionStats | None = None,
        theme_name: str = "github-dark",
        no_color: bool = False,
        ascii_mode: bool = False,
        show_stats: bool = True,
        compact: bool = False,
        output_format: str = "terminal",
    ) -> None:
        """Render contribution calendar to configured destination."""
        if stats is None:
            stats = StatisticsEngine.calculate(calendar)

        if output_format.lower() == "json":
            self._render_json(calendar, stats)
            return

        if output_format.lower() == "csv":
            self._render_csv(calendar)
            return

        theme = get_theme(theme_name, no_color=no_color, ascii_mode=ascii_mode)
        term_width = self.console.width if (self.console and self.console.width) else get_terminal_width()

        # Render Header Info
        if not compact:
            self._render_header(calendar, stats, theme)

        # Decide whether to split into halves based on terminal width
        total_weeks = len(calendar.weeks)
        required_width = 6 + (total_weeks * 2)

        if required_width > term_width and total_weeks > 26:
            # Render split view: Weeks 0-25 (H1) and Weeks 26+ (H2)
            half = total_weeks // 2
            self.console.print("\n[bold cyan]Part 1: Early Period[/bold cyan]")
            self._render_matrix_block(calendar.weeks[:half], calendar.months, 0, theme)
            self.console.print("\n[bold cyan]Part 2: Later Period[/bold cyan]")
            self._render_matrix_block(calendar.weeks[half:], calendar.months, half, theme)
        else:
            self._render_matrix_block(calendar.weeks, calendar.months, 0, theme)

        # Render Legend
        self._render_legend(theme)

        # Render Summary Statistics
        if show_stats and not compact:
            self._render_stats_card(stats)

    def _render_header(
        self,
        calendar: ContributionCalendar,
        stats: ContributionStats,
        theme: ColorTheme,
    ) -> None:
        """Render header panel with username and key totals."""
        period_str = str(calendar.year) if calendar.year else f"{calendar.from_date} to {calendar.to_date}"
        title = f"[bold white]GitHub Contributions[/bold white] [dim]•[/dim] [bold cyan]@{calendar.username}[/bold cyan] [dim]({period_str})[/dim]"

        summary_text = (
            f"[bold green]{stats.total_contributions:,}[/bold green] contributions in this period "
            f"([bold yellow]{stats.current_streak}[/bold yellow] day current streak, "
            f"[bold magenta]{stats.longest_streak}[/bold magenta] day longest streak)"
        )
        self.console.print(Panel(summary_text, title=title, border_style="cyan", expand=False))

    def _render_matrix_block(
        self,
        weeks: list[ContributionWeek],
        all_months: list,
        start_week_offset: int,
        theme: ColorTheme,
    ) -> None:
        """Render a single block of weeks with aligned month headers."""
        if not weeks:
            return

        num_weeks = len(weeks)

        # Build Month Header Line
        month_line = ["    "]  # 4 chars for left margin
        month_chars = [" "] * (num_weeks * 2)

        for m in all_months:
            rel_idx = m.first_week_idx - start_week_offset
            if 0 <= rel_idx < num_weeks:
                pos = rel_idx * 2
                name = m.name[:3]
                for i, char in enumerate(name):
                    if pos + i < len(month_chars):
                        month_chars[pos + i] = char

        month_text = Text("    " + "".join(month_chars), style="dim")
        self.console.print(month_text)

        # Render 7 Weekday Rows
        for day_idx in range(7):
            row_text = Text()
            row_label = self.ROW_LABELS[day_idx]
            row_text.append(f"{row_label} ", style="dim")

            for week in weeks:
                # Find day matching this weekday (0=Sun, 1=Mon, ..., 6=Sat)
                day_match = None
                for d in week.days:
                    if d.weekday == day_idx:
                        day_match = d
                        break

                if day_match is not None:
                    lvl = max(0, min(4, day_match.level))
                    char = theme.chars[lvl]
                    color = theme.colors[lvl]
                    if theme.name == "monochrome":
                        row_text.append(f"{char} ")
                    else:
                        row_text.append(f"{char} ", style=color)
                else:
                    row_text.append("  ")

            self.console.print(row_text)

    def _render_legend(self, theme: ColorTheme) -> None:
        """Render bottom density legend."""
        legend = Text("\n      Less ", style="dim")
        for lvl in range(5):
            char = theme.chars[lvl]
            color = theme.colors[lvl]
            if theme.name == "monochrome":
                legend.append(f"{char} ")
            else:
                legend.append(f"{char} ", style=color)
        legend.append("More\n", style="dim")
        self.console.print(legend)

    def _render_stats_card(self, stats: ContributionStats) -> None:
        """Render activity statistics table."""
        table = Table(title="Activity Insights", border_style="dim", box=None, padding=(0, 2))
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="bold white")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="bold white")

        table.add_row("Total Contributions", f"{stats.total_contributions:,}", "Active Days", f"{stats.active_days:,} / {stats.total_days} ({stats.active_days_percentage}%)")
        table.add_row("Current Streak", f"{stats.current_streak} days", "Longest Streak", f"{stats.longest_streak} days")
        table.add_row("Daily Average", f"{stats.average_per_day} / day", "Weekly Average", f"{stats.average_per_week} / week")
        table.add_row("Peak Activity Day", f"{stats.max_day or 'N/A'} ({stats.max_count} items)", "Most Active Weekday", stats.most_active_weekday)

        if stats.total_commits or stats.total_prs or stats.total_issues or stats.total_reviews:
            table.add_row("Commits", f"{stats.total_commits:,}", "Pull Requests", f"{stats.total_prs:,}")
            table.add_row("Issues", f"{stats.total_issues:,}", "Code Reviews", f"{stats.total_reviews:,}")

        self.console.print(table)
        self.console.print("")

    def _render_json(self, calendar: ContributionCalendar, stats: ContributionStats) -> None:
        """Output calendar and stats as JSON."""
        output = {
            "calendar": calendar.to_dict(),
            "statistics": stats.to_dict(),
        }
        print(json.dumps(output, indent=2))

    def _render_csv(self, calendar: ContributionCalendar) -> None:
        """Output flat contribution days as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "weekday", "count", "level"])
        for day in calendar.all_days():
            writer.writerow([day.date, day.weekday, day.count, day.level])
        print(output.getvalue().strip())
