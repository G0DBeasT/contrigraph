"""Terminal rendering engine for GitHub contribution calendars."""

from __future__ import annotations

import csv
import io
import json
import math

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from contrigraph.models.calendar import (
    ContributionCalendar,
    ContributionStats,
    ContributionWeek,
)
from contrigraph.rendering.themes import THEMES, ColorTheme, get_theme
from contrigraph.statistics.engine import StatisticsEngine
from contrigraph.utils.platform import TerminalCapabilities, get_terminal_width, supports_unicode


class CalendarRenderer:
    """Renders contribution calendars to terminal or export formats."""

    # Weekday display labels (0=Sunday, 1=Monday, ..., 6=Saturday)
    ROW_LABELS = ["   ", "Mon", "   ", "Wed", "   ", "Fri", "   "]

    def __init__(
        self,
        console: Console | None = None,
        capabilities: TerminalCapabilities | None = None,
    ) -> None:
        if capabilities is not None:
            self.capabilities = capabilities
            self.console = console or capabilities.create_console()
        elif console is not None:
            self.console = console
            self.capabilities = TerminalCapabilities.detect(console=console)
        else:
            self.capabilities = TerminalCapabilities.detect()
            self.console = self.capabilities.create_console()

    def _is_unicode_supported(self, theme: ColorTheme | None = None, ascii_mode: bool = False) -> bool:
        """Check if Unicode rendering is supported by terminal, encoding, and theme."""
        if ascii_mode:
            return False
        if theme and theme.is_ascii:
            return False
        return self.capabilities.supports_unicode

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

        caps = self.capabilities
        theme = get_theme(theme_name, no_color=no_color, ascii_mode=ascii_mode, capabilities=caps)
        term_width = self.console.width if (self.console and self.console.width) else caps.width
        is_unicode = self._is_unicode_supported(theme=theme, ascii_mode=ascii_mode)
        if not is_unicode and not theme.is_ascii:
            theme = THEMES["ascii"]

        # Render Header Info
        if not compact:
            self._render_header(calendar, stats, theme, is_unicode=is_unicode)

        # Dynamic terminal-width chunking
        total_weeks = len(calendar.weeks)
        if total_weeks > 0:
            label_width = 4
            safety_padding = 2
            required_full_width = label_width + (total_weeks * 2)

            if required_full_width <= term_width:
                chunks = [(0, total_weeks)]
            else:
                max_weeks_per_chunk = caps.get_max_weeks_per_chunk(label_width, safety_padding)
                num_chunks = max(2, math.ceil(total_weeks / max_weeks_per_chunk))

                base_size = total_weeks // num_chunks
                remainder = total_weeks % num_chunks
                chunks = []
                curr = 0
                for i in range(num_chunks):
                    chunk_len = base_size + (1 if i < remainder else 0)
                    chunks.append((curr, curr + chunk_len))
                    curr += chunk_len

            if len(chunks) == 1:
                self._render_matrix_block(calendar.weeks, calendar.months, 0, theme)
            else:
                arrow = caps.arrow_char if is_unicode else "->"
                for idx, (start_idx, end_idx) in enumerate(chunks):
                    start_date = None
                    for d in calendar.weeks[start_idx].days:
                        if d.date:
                            start_date = d.date
                            break
                    end_date = None
                    for d in reversed(calendar.weeks[end_idx - 1].days):
                        if d.date:
                            end_date = d.date
                            break

                    date_str = f" ({start_date} {arrow} {end_date})" if (start_date and end_date) else ""

                    if len(chunks) == 2:
                        period_name = "Early Period" if idx == 0 else "Later Period"
                        header_title = f"Part {idx + 1}: {period_name}{date_str}"
                    else:
                        header_title = f"Part {idx + 1} of {len(chunks)}{date_str}"

                    self.console.print(f"\n[bold cyan]{header_title}[/bold cyan]")
                    self._render_matrix_block(calendar.weeks[start_idx:end_idx], calendar.months, start_idx, theme)

        # Render Legend
        self._render_legend(theme)

        # Render Summary Statistics
        if show_stats and not compact:
            self._render_stats_card(stats)

    def _render_header(
        self,
        calendar: ContributionCalendar,
        stats: ContributionStats,
        theme: ColorTheme | None = None,
        is_unicode: bool | None = None,
    ) -> None:
        """Render header panel with username and key totals."""
        if is_unicode is None:
            is_unicode = self._is_unicode_supported(theme=theme)

        bullet = self.capabilities.bullet_char if is_unicode else "*"
        period_str = str(calendar.year) if calendar.year else f"{calendar.from_date} to {calendar.to_date}"
        title = f"[bold white]GitHub Contributions[/bold white] [dim]{bullet}[/dim] [bold cyan]@{calendar.username}[/bold cyan] [dim]({period_str})[/dim]"

        summary_text = (
            f"[bold green]{stats.total_contributions:,}[/bold green] contributions in this period "
            f"([bold yellow]{stats.current_streak}[/bold yellow] day current streak, "
            f"[bold magenta]{stats.longest_streak}[/bold magenta] day longest streak)"
        )
        panel_box = self.capabilities.box_style if is_unicode else box.ASCII
        self.console.print(Panel(summary_text, title=title, border_style="cyan", expand=False, box=panel_box))

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
        month_chars = [" "] * (num_weeks * 2)

        for m in all_months:
            rel_idx = m.first_week_idx - start_week_offset
            if 0 <= rel_idx < num_weeks:
                pos = rel_idx * 2
                name = m.name[:3]
                for i, char in enumerate(name):
                    if pos + i < len(month_chars):
                        month_chars[pos + i] = char
            elif m.first_week_idx < start_week_offset and (m.first_week_idx + m.total_weeks) > start_week_offset:
                # Spanning month from previous block: show at start if room exists
                name = m.name[:3]
                first_inner = min(
                    (other.first_week_idx - start_week_offset for other in all_months
                     if 0 <= (other.first_week_idx - start_week_offset) < num_weeks),
                    default=num_weeks,
                )
                if first_inner >= 2:
                    for i, char in enumerate(name):
                        if i < len(month_chars):
                            month_chars[i] = char

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
