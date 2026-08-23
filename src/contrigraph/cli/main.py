"""Main CLI entrypoint for contrigraph / ghcontrib."""

import argparse
import getpass
import sys
from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

import contrigraph
from contrigraph.api.client import GitHubClient
from contrigraph.auth.manager import AuthManager
from contrigraph.cache.manager import CacheManager
from contrigraph.cli.doctor import Doctor
from contrigraph.config.manager import ConfigManager, UserConfig
from contrigraph.rendering.renderer import CalendarRenderer
from contrigraph.rendering.themes import THEMES
from contrigraph.statistics.engine import StatisticsEngine
from contrigraph.utils.errors import (
    AuthError,
    ConfigError,
    ConfigNotFoundError,
    ContrigraphError,
    MissingTokenError,
)

console = Console()


def cmd_setup(args: argparse.Namespace) -> int:
    """Handle setup command to configure user preferences."""
    config_mgr = ConfigManager()
    console.print(Panel("[bold white]Contrigraph Setup[/bold white]", border_style="cyan", expand=False))

    username = args.username
    if not username:
        if sys.stdin.isatty():
            username = Prompt.ask("[bold cyan]Enter your GitHub username[/bold cyan]")
        else:
            username = ""
    username = (username or "").strip()

    if not username:
        console.print("[bold red]Error:[/bold red] Username is required for setup.")
        return 1

    email = args.email
    if email is None:
        if sys.stdin.isatty():
            email = Prompt.ask("[bold cyan]Enter your email (optional, application metadata)[/bold cyan]", default="")
        else:
            email = ""
    email = (email or "").strip()

    theme = args.theme or "github-dark"
    if theme not in THEMES:
        theme = "github-dark"

    cfg = UserConfig(username=username, email=email, theme=theme)
    config_mgr.save_config(cfg)
    console.print(f"\n[bold green]✓ Configuration saved successfully for @{username}![/bold green]")
    console.print("[dim]Next, run [bold]ghcontrib auth login[/bold] to authenticate securely with GitHub.[/dim]\n")
    return 0


def cmd_auth(args: argparse.Namespace) -> int:
    """Handle auth subcommands (login, status, logout)."""
    action = args.auth_action or "status"
    auth_mgr = AuthManager()

    if action == "status":
        status = auth_mgr.get_auth_status()
        console.print(Panel("[bold white]GitHub Authentication Status[/bold white]", border_style="cyan", expand=False))
        if status.is_authenticated:
            console.print(f"Status: [bold green]Authenticated[/bold green]")
            console.print(f"Source: [cyan]{status.source}[/cyan]")
            if status.username:
                console.print(f"User:   [bold white]@{status.username}[/bold white]")
            if status.scopes:
                console.print(f"Scopes: [dim]{', '.join(status.scopes)}[/dim]")
            if status.masked_token:
                console.print(f"Token:  [dim]{status.masked_token}[/dim]")
        else:
            console.print(f"Status: [bold yellow]Not Authenticated[/bold yellow]")
            console.print(f"Run [bold green]ghcontrib auth login[/bold green] to authenticate.\n")
        return 0

    elif action == "login":
        console.print(Panel("[bold white]GitHub Authentication[/bold white]", border_style="cyan", expand=False))
        console.print("[dim]Contrigraph uses GitHub Personal Access Tokens (PAT).[/dim]")
        console.print("[dim]Create a token at: [underline]https://github.com/settings/tokens[/underline][/dim]")
        console.print("[dim]Required permissions: Public data (read-only) or read:user (optional, for private counts).[/dim]\n")

        token = args.token
        if not token:
            try:
                token = getpass.getpass("Enter your GitHub Personal Access Token (hidden): ")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Authentication cancelled.[/yellow]")
                return 1

        token = token.strip()
        if not token:
            console.print("[bold red]Error:[/bold red] Token cannot be empty.")
            return 1

        try:
            with console.status("[bold green]Validating token with GitHub...[/bold green]"):
                creds = auth_mgr.login(token, validate=not args.no_validate)
            user_msg = f" as @{creds.username}" if creds.username else ""
            console.print(f"\n[bold green]✓ Successfully authenticated{user_msg}![/bold green]")
            console.print(f"[dim]Credentials securely stored in {auth_mgr.auth_path}[/dim]\n")
            return 0
        except AuthError as err:
            console.print(f"\n[bold red]Authentication failed:[/bold red] {err}")
            return 1

    elif action == "logout":
        auth_mgr.logout()
        console.print("[bold green]✓ Stored authentication credentials removed.[/bold green]\n")
        return 0

    return 0


def _fetch_calendar(
    username: str,
    year: int | None,
    force_refresh: bool = False,
    cache_ttl_hours: int = 4,
) -> tuple[any, bool]:
    """Helper to retrieve calendar from cache or API."""
    cache_mgr = CacheManager()
    auth_mgr = AuthManager()

    if not force_refresh:
        cached_cal = cache_mgr.get(username, year, ttl_hours=cache_ttl_hours)
        if cached_cal is not None:
            return cached_cal, True

    token = auth_mgr.get_token()
    client = GitHubClient(token=token)
    calendar = client.fetch_contributions(username=username, year=year)
    cache_mgr.set(calendar)
    return calendar, False


def cmd_show(args: argparse.Namespace) -> int:
    """Display the contribution calendar graph and stats."""
    config_mgr = ConfigManager()
    if not config_mgr.is_configured() and not args.username:
        console.print("[bold yellow]Contrigraph is not configured yet.[/bold yellow]")
        if sys.stdin.isatty() and Prompt.ask("Would you like to run first-time setup now?", choices=["y", "n"], default="y") == "y":
            cmd_setup(args)
        else:
            console.print("[dim]Run [bold]ghcontrib setup[/bold] to configure your username or provide [bold]--user <name>[/bold].[/dim]")
            return 1

    cfg = config_mgr.load_config() if config_mgr.is_configured() else None
    username = args.username or (cfg.username if cfg else None)
    if not username:
        console.print("[bold red]Error:[/bold red] No GitHub username specified. Run 'ghcontrib setup' or use --user.")
        return 1

    year = args.year if args.year is not None else (cfg.default_year if cfg else None)
    theme = args.theme or (cfg.theme if cfg else "github-dark")
    compact = args.compact or (cfg.compact_mode if cfg else False)
    show_stats = False if args.no_stats else (cfg.show_stats if cfg else True)
    output_format = args.format or "terminal"

    calendar, is_cached = _fetch_calendar(
        username=username,
        year=year,
        force_refresh=args.refresh,
        cache_ttl_hours=cfg.cache_ttl_hours if cfg else 4,
    )

    renderer = CalendarRenderer(console=console)
    renderer.render(
        calendar=calendar,
        theme_name=theme,
        no_color=args.no_color,
        ascii_mode=args.ascii,
        show_stats=show_stats,
        compact=compact,
        output_format=output_format,
    )
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Display activity statistics only."""
    config_mgr = ConfigManager()
    cfg = config_mgr.load_config() if config_mgr.is_configured() else None
    username = args.username or (cfg.username if cfg else None)
    if not username:
        console.print("[bold red]Error:[/bold red] No GitHub username specified. Run 'ghcontrib setup' or use --user.")
        return 1

    year = args.year if args.year is not None else (cfg.default_year if cfg else None)
    calendar, _ = _fetch_calendar(
        username=username,
        year=year,
        force_refresh=args.refresh,
        cache_ttl_hours=cfg.cache_ttl_hours if cfg else 4,
    )

    stats = StatisticsEngine.calculate(calendar)
    renderer = CalendarRenderer(console=console)
    renderer._render_header(calendar, stats, None)
    renderer._render_stats_card(stats)
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    """Force refresh cache and display updated graph."""
    args.refresh = True
    return cmd_show(args)


def cmd_config(args: argparse.Namespace) -> int:
    """View or update configuration settings."""
    config_mgr = ConfigManager()
    action = args.config_action or "show"

    if action == "show":
        if not config_mgr.is_configured():
            console.print("[yellow]No configuration found. Run 'ghcontrib setup'.[/yellow]")
            return 0
        cfg = config_mgr.load_config()
        console.print(Panel("[bold white]Contrigraph Configuration[/bold white]", border_style="cyan", expand=False))
        console.print(f"Username:     [bold white]@{cfg.username}[/bold white]")
        console.print(f"Email:        [dim]{cfg.email or 'Not set'}[/dim]")
        console.print(f"Theme:        [cyan]{cfg.theme}[/cyan]")
        console.print(f"Default Year: [white]{cfg.default_year or 'Current / Recent'}[/white]")
        console.print(f"Cache TTL:    [white]{cfg.cache_ttl_hours} hours[/white]")
        console.print(f"Config File:  [dim]{config_mgr.config_path}[/dim]\n")
        return 0

    elif action == "set":
        if not hasattr(args, "key") or not args.key:
            console.print("[bold red]Usage:[/bold red] ghcontrib config set <key> <value>")
            return 1
        key = args.key
        val = args.val
        if key == "theme" and val not in THEMES:
            console.print(f"[bold red]Error:[/bold red] Unknown theme '{val}'. Available: {', '.join(THEMES.keys())}")
            return 1
        try:
            config_mgr.update_config(**{key: val})
            console.print(f"[bold green]✓ Updated {key} = {val}[/bold green]")
        except Exception as err:
            console.print(f"[bold red]Failed to update config:[/bold red] {err}")
            return 1
        return 0

    elif action == "reset":
        config_mgr.reset_config()
        console.print("[bold green]✓ Configuration has been reset.[/bold green]")
        return 0

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run environment and connection diagnostics."""
    doc = Doctor(console=console)
    success = doc.run_diagnostics()
    return 0 if success else 1


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="ghcontrib",
        description="GitHub Contribution Graph CLI for Fedora and modern terminals.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed debug trace on errors")
    parser.add_argument("--version", action="version", version=f"contrigraph {contrigraph.__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. setup
    p_setup = subparsers.add_parser("setup", help="First-time setup for username and preferences")
    p_setup.add_argument("--user", "--username", dest="username", help="GitHub username")
    p_setup.add_argument("--email", dest="email", help="User email address")
    p_setup.add_argument("--theme", dest="theme", choices=list(THEMES.keys()), help="Color theme")

    # 2. auth
    p_auth = subparsers.add_parser("auth", help="Manage GitHub authentication")
    p_auth.add_argument("auth_action", nargs="?", choices=["login", "status", "logout"], default="status", help="Auth action")
    p_auth.add_argument("--token", help="GitHub Personal Access Token")
    p_auth.add_argument("--no-validate", action="store_true", help="Skip remote token validation during login")

    # 3. show
    p_show = subparsers.add_parser("show", help="Display contribution calendar")
    p_show.add_argument("--user", "--username", dest="username", help="Target GitHub username")
    p_show.add_argument("--year", type=int, help="Target calendar year (e.g. 2026)")
    p_show.add_argument("--theme", choices=list(THEMES.keys()), help="Color theme")
    p_show.add_argument("--no-color", action="store_true", help="Disable color output")
    p_show.add_argument("--ascii", action="store_true", help="Render using plain ASCII characters")
    p_show.add_argument("--compact", action="store_true", help="Render graph only without header/stats")
    p_show.add_argument("--no-stats", action="store_true", help="Hide statistics table")
    p_show.add_argument("--refresh", action="store_true", help="Force fresh data from GitHub API")
    p_show.add_argument("--format", choices=["terminal", "json", "csv"], default="terminal", help="Output format")

    # 4. stats
    p_stats = subparsers.add_parser("stats", help="Display contribution activity statistics only")
    p_stats.add_argument("--user", "--username", dest="username", help="Target GitHub username")
    p_stats.add_argument("--year", type=int, help="Target calendar year")
    p_stats.add_argument("--refresh", action="store_true", help="Force refresh data")

    # 5. refresh
    p_refresh = subparsers.add_parser("refresh", help="Force fresh data from GitHub and update graph")
    p_refresh.add_argument("--user", "--username", dest="username", help="Target GitHub username")
    p_refresh.add_argument("--year", type=int, help="Target calendar year")
    p_refresh.add_argument("--theme", choices=list(THEMES.keys()), help="Color theme")
    p_refresh.add_argument("--no-color", action="store_true", help="Disable color output")
    p_refresh.add_argument("--ascii", action="store_true", help="Render using plain ASCII characters")
    p_refresh.add_argument("--compact", action="store_true", help="Render graph only")
    p_refresh.add_argument("--no-stats", action="store_true", help="Hide statistics table")
    p_refresh.add_argument("--format", choices=["terminal", "json", "csv"], default="terminal", help="Output format")

    # 6. config
    p_config = subparsers.add_parser("config", help="View or modify user configuration")
    p_config.add_argument("config_action", nargs="?", choices=["show", "set", "reset"], default="show")
    p_config.add_argument("key", nargs="?", help="Configuration key to set")
    p_config.add_argument("val", nargs="?", help="Configuration value")

    # 7. doctor
    subparsers.add_parser("doctor", help="Run system, environment, and network diagnostics")

    # 8. version
    subparsers.add_parser("version", help="Show version information")

    return parser


def main(args: Sequence[str] | None = None) -> int:
    """CLI main entry point with global exception handling."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    cmd = parsed_args.command

    try:
        if cmd == "setup":
            return cmd_setup(parsed_args)
        elif cmd == "auth":
            return cmd_auth(parsed_args)
        elif cmd == "show":
            return cmd_show(parsed_args)
        elif cmd == "stats":
            return cmd_stats(parsed_args)
        elif cmd == "refresh":
            return cmd_refresh(parsed_args)
        elif cmd == "config":
            return cmd_config(parsed_args)
        elif cmd == "doctor":
            return cmd_doctor(parsed_args)
        elif cmd == "version":
            console.print(f"contrigraph [bold cyan]{contrigraph.__version__}[/bold cyan]")
            return 0
        else:
            # Default behavior when no subcommand given: 'show'
            # Add default attributes expected by cmd_show
            parsed_args.username = None
            parsed_args.year = None
            parsed_args.theme = None
            parsed_args.no_color = False
            parsed_args.ascii = False
            parsed_args.compact = False
            parsed_args.no_stats = False
            parsed_args.refresh = False
            parsed_args.format = "terminal"
            return cmd_show(parsed_args)

    except ContrigraphError as err:
        if parsed_args.verbose:
            console.print_exception()
        else:
            console.print(Panel(str(err), title="[bold red]Contrigraph Error[/bold red]", border_style="red", expand=False))
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation aborted by user.[/yellow]")
        return 130
    except Exception as err:
        if parsed_args.verbose:
            console.print_exception()
        else:
            console.print(
                Panel(
                    f"An unexpected error occurred: {err}\n\n[dim]Run with [bold]--verbose[/bold] for full diagnostic trace.[/dim]",
                    title="[bold red]Unexpected Error[/bold red]",
                    border_style="red",
                    expand=False,
                )
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
