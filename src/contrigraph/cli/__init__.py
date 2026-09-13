"""CLI package for contrigraph."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from contrigraph.cli.main import build_parser, main

__all__ = ["build_parser", "main"]


def __getattr__(name: str) -> Any:
    """Lazy-load CLI entrypoints to avoid eager import side effects."""
    if name in ("build_parser", "main"):
        from contrigraph.cli.main import build_parser, main

        mapping = {"build_parser": build_parser, "main": main}
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
