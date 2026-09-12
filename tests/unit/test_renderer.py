"""Unit tests for terminal renderer and themes."""

import io
from rich.console import Console

from contrigraph.data.normalizer import ContributionNormalizer
from contrigraph.rendering.renderer import CalendarRenderer
from contrigraph.rendering.themes import get_theme
from tests.fixtures.mock_data import make_mock_calendar_payload


def test_theme_resolution(monkeypatch):
    """Verify theme fallback and selection."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    t_dark = get_theme("github-dark")
    assert t_dark.name == "github-dark"
    assert len(t_dark.colors) == 5

    t_ascii = get_theme(ascii_mode=True)
    assert t_ascii.is_ascii
    assert t_ascii.chars == (".", "o", "O", "#", "@")

    t_mono = get_theme(no_color=True)
    assert t_mono.name == "monochrome"

    # Test NO_COLOR environment variable
    monkeypatch.setenv("NO_COLOR", "1")
    assert get_theme("github-dark").name == "monochrome"
    monkeypatch.delenv("NO_COLOR", raising=False)

    # Test TERM=dumb environment variable
    monkeypatch.setenv("TERM", "dumb")
    assert get_theme("github-dark").name == "monochrome"
    monkeypatch.delenv("TERM", raising=False)


def test_renderer_no_color_environment(monkeypatch):
    """Verify renderer uses monochrome symbol gradation when NO_COLOR is set."""
    monkeypatch.setenv("NO_COLOR", "1")
    payload = make_mock_calendar_payload("monouser", total_contributions=100)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "monouser", 2026)

    string_io = io.StringIO()
    console = Console(file=string_io, color_system=None, width=120)
    renderer = CalendarRenderer(console=console)

    renderer.render(calendar=cal, theme_name="github-dark", show_stats=False)
    output = string_io.getvalue()
    # Level 0 should use '·'
    assert "·" in output


def test_renderer_output_terminal():
    """Verify terminal rendering without exceptions."""
    payload = make_mock_calendar_payload("renderuser", total_contributions=300)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "renderuser", 2026)

    string_io = io.StringIO()
    console = Console(file=string_io, color_system=None, width=120)
    renderer = CalendarRenderer(console=console)

    renderer.render(calendar=cal, theme_name="github-dark", show_stats=True)
    output = string_io.getvalue()
    assert "renderuser" in output
    assert "300" in output
    assert "Activity Insights" in output
    # Month headers in 120-col view should include Jan at start, Jun in middle, Dec at end
    assert "Jan" in output
    assert "Jun" in output
    assert "Dec" in output


def test_renderer_month_headers_split_view():
    """Verify split view (width < 110) renders month headers in both Part 1 and Part 2."""
    payload = make_mock_calendar_payload("splituser", total_contributions=250)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "splituser", 2026)

    string_io = io.StringIO()
    console = Console(file=string_io, color_system=None, width=80)
    renderer = CalendarRenderer(console=console)

    renderer.render(calendar=cal, theme_name="github-dark", show_stats=False)
    output = string_io.getvalue()

    assert "Part 1: Early Period" in output
    assert "Part 2: Later Period" in output
    # Part 1 should have first half months, Part 2 should have second half months
    part1_section = output.split("Part 2: Later Period")[0]
    part2_section = output.split("Part 2: Later Period")[1]
    assert "Jan" in part1_section
    assert "Jun" in part1_section
    assert "Aug" in part2_section
    assert "Dec" in part2_section



def test_renderer_formats_json_and_csv(capsys):
    """Verify JSON and CSV export formats."""
    payload = make_mock_calendar_payload("exportuser", total_contributions=150)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "exportuser", 2026)
    renderer = CalendarRenderer()

    # JSON
    renderer.render(calendar=cal, output_format="json")
    out_json, _ = capsys.readouterr()
    assert '"username": "exportuser"' in out_json
    assert '"total_contributions": 150' in out_json

    # CSV
    renderer.render(calendar=cal, output_format="csv")
    out_csv, _ = capsys.readouterr()
    assert "date,weekday,count,level" in out_csv


def test_calendar_renderer_type_hints():
    """Verify runtime type hints can be evaluated without NameError."""
    import typing
    hints = typing.get_type_hints(CalendarRenderer._render_matrix_block)
    assert "weeks" in hints
    assert hints["return"] is type(None)


def test_dynamic_terminal_width_chunking():
    """Verify calendar dynamically chunks to fit terminal width without line wrapping."""
    payload = make_mock_calendar_payload("narrowuser", total_contributions=300)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "narrowuser", 2026)

    test_widths = [120, 100, 80, 70, 60, 50, 45, 40, 35, 30]

    for width in test_widths:
        string_io = io.StringIO()
        console = Console(file=string_io, color_system=None, width=width)
        renderer = CalendarRenderer(console=console)

        renderer.render(calendar=cal, theme_name="ascii", show_stats=False, compact=True)
        output = string_io.getvalue()

        # Check that each printed row in the matrix does not exceed terminal width
        for line in output.splitlines():
            # Weekday rows start with 3 spaces or weekday label + space (e.g. "Mon ", "   ")
            if any(line.startswith(prefix) for prefix in ("Mon ", "Wed ", "Fri ", "    ")):
                assert len(line) <= width, f"Line '{line}' (len={len(line)}) exceeded terminal width {width}"

    # Verify specific chunk counts for key responsive breakpoints
    # Width 120 -> 1 chunk (no Part headers)
    s120 = io.StringIO()
    CalendarRenderer(console=Console(file=s120, color_system=None, width=120)).render(cal, compact=True, show_stats=False)
    assert "Part 1" not in s120.getvalue()

    # Width 80 -> 2 chunks
    s80 = io.StringIO()
    CalendarRenderer(console=Console(file=s80, color_system=None, width=80)).render(cal, compact=True, show_stats=False)
    assert "Part 1: Early Period" in s80.getvalue()
    assert "Part 2: Later Period" in s80.getvalue()

    # Width 50 (Termux portrait) -> 3 chunks
    s50 = io.StringIO()
    CalendarRenderer(console=Console(file=s50, color_system=None, width=50)).render(cal, compact=True, show_stats=False)
    assert "Part 1 of 3" in s50.getvalue()
    assert "Part 2 of 3" in s50.getvalue()
    assert "Part 3 of 3" in s50.getvalue()

    # Width 45 (Narrow smartphone Termux) -> 3 chunks
    s45 = io.StringIO()
    CalendarRenderer(console=Console(file=s45, color_system=None, width=45)).render(cal, compact=True, show_stats=False)
    assert "Part 1 of 3" in s45.getvalue()

    # Width 35 (Very narrow split pane) -> 4 chunks
    s35 = io.StringIO()
    CalendarRenderer(console=Console(file=s35, color_system=None, width=35)).render(cal, compact=True, show_stats=False)
    assert "Part 1 of 4" in s35.getvalue()
    assert "Part 4 of 4" in s35.getvalue()
