"""Color palettes and symbol themes for terminal rendering."""

import os
from dataclasses import dataclass

from contrigraph.utils.platform import TerminalCapabilities, supports_unicode


@dataclass(frozen=True)
class ColorTheme:
    """Defines 5 density colors and level symbols."""

    name: str
    description: str
    # Hex or ANSI color strings for levels 0 to 4
    colors: tuple[str, str, str, str, str]
    # Characters used for levels 0 to 4
    chars: tuple[str, str, str, str, str]
    is_ascii: bool = False


# Theme catalog
THEMES: dict[str, ColorTheme] = {
    "github-dark": ColorTheme(
        name="github-dark",
        description="Standard GitHub Dark theme (TrueColor green blocks)",
        colors=("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"),
        chars=("■", "■", "■", "■", "■"),
    ),
    "github-light": ColorTheme(
        name="github-light",
        description="Standard GitHub Light theme",
        colors=("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"),
        chars=("■", "■", "■", "■", "■"),
    ),
    "emerald": ColorTheme(
        name="emerald",
        description="Vibrant Emerald / Mint palette",
        colors=("#112211", "#004b49", "#008170", "#00b894", "#55efc4"),
        chars=("■", "■", "■", "■", "■"),
    ),
    "halloween": ColorTheme(
        name="halloween",
        description="GitHub Halloween pumpkin orange theme",
        colors=("#161b22", "#631c03", "#bd561d", "#fa7a18", "#fddf68"),
        chars=("■", "■", "■", "■", "■"),
    ),
    "unicode-blocks": ColorTheme(
        name="unicode-blocks",
        description="Classic Unicode shading block characters",
        colors=("#444444", "#0e4429", "#006d32", "#26a641", "#39d353"),
        chars=("░", "░", "▒", "▓", "█"),
    ),
    "ascii": ColorTheme(
        name="ascii",
        description="Plain ASCII fallback for non-Unicode terminals",
        colors=("white", "green", "green", "bright_green", "bright_green"),
        chars=(".", "o", "O", "#", "@"),
        is_ascii=True,
    ),
    "monochrome": ColorTheme(
        name="monochrome",
        description="No-color monochrome blocks",
        colors=("white", "white", "white", "white", "white"),
        chars=("·", "▪", "■", "█", "█"),
        is_ascii=False,
    ),
}


def get_theme(
    name: str = "github-dark",
    no_color: bool = False,
    ascii_mode: bool = False,
    capabilities: TerminalCapabilities | None = None,
) -> ColorTheme:
    """Resolve theme based on flags, preferences, and terminal capabilities."""
    caps = capabilities or TerminalCapabilities.detect()
    if ascii_mode or not caps.supports_unicode or not supports_unicode() or os.environ.get("TERM") == "dumb":
        return THEMES["ascii"]
    if no_color or "NO_COLOR" in os.environ or not caps.supports_color:
        return THEMES["monochrome"]
    return THEMES.get(name.lower(), THEMES["github-dark"])
