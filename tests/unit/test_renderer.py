"""Unit tests for terminal renderer and themes."""

import io
from rich.console import Console

from contrigraph.data.normalizer import ContributionNormalizer
from contrigraph.rendering.renderer import CalendarRenderer
from contrigraph.rendering.themes import THEMES, get_theme
from tests.fixtures.mock_data import make_mock_calendar_payload


def test_theme_resolution():
    """Verify theme fallback and selection."""
    t_dark = get_theme("github-dark")
    assert t_dark.name == "github-dark"
    assert len(t_dark.colors) == 5

    t_ascii = get_theme(ascii_mode=True)
    assert t_ascii.is_ascii
    assert t_ascii.chars == (".", "o", "O", "#", "@")

    t_mono = get_theme(no_color=True)
    assert t_mono.name == "monochrome"


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
