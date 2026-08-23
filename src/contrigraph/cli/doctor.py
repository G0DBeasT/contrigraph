"""Doctor command to diagnose environment, auth, network, and terminal health."""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from contrigraph.api.client import GitHubClient
from contrigraph.auth.manager import AuthManager
from contrigraph.config.manager import ConfigManager
from contrigraph.utils.platform import (
    PlatformPaths,
    get_terminal_width,
    supports_color,
    supports_truecolor,
    supports_unicode,
)


class Doctor:
    """Diagnoses system, configuration, authentication, and network status."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.config_mgr = ConfigManager()
        self.auth_mgr = AuthManager()

    def run_diagnostics(self) -> bool:
        """Run complete diagnostic suite and display results."""
        self.console.print(Panel("[bold white]Contrigraph System Doctor[/bold white]", border_style="cyan", expand=False))

        table = Table(box=None, padding=(0, 2), show_header=True)
        table.add_column("Category", style="bold cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details", style="dim white")

        all_ok = True

        # 1. Python Environment
        py_ver = sys.version.split()[0]
        if sys.version_info >= (3, 10):
            table.add_row("Python Version", "[green]✓ OK[/green]", f"Python {py_ver} ({sys.executable})")
        else:
            table.add_row("Python Version", "[red]✗ FAIL[/red]", f"Python {py_ver} is < 3.10. Upgrade required.")
            all_ok = False

        # 2. Operating System / Paths
        config_dir = PlatformPaths.get_config_dir()
        cache_dir = PlatformPaths.get_cache_dir()
        table.add_row("OS Platform", "[green]✓ OK[/green]", f"{sys.platform} (Config: {config_dir})")

        # 3. Configuration
        if self.config_mgr.is_configured():
            try:
                cfg = self.config_mgr.load_config()
                table.add_row("Configuration", "[green]✓ OK[/green]", f"User: @{cfg.username} (Theme: {cfg.theme})")
            except Exception as err:
                table.add_row("Configuration", "[red]✗ CORRUPT[/red]", str(err))
                all_ok = False
        else:
            table.add_row("Configuration", "[yellow]! NOT SET[/yellow]", "Run 'ghcontrib setup' to initialize")
            all_ok = False

        # 4. Authentication & Credentials
        auth_status = self.auth_mgr.get_auth_status()
        token = self.auth_mgr.get_token()

        if auth_status.is_authenticated and token:
            table.add_row("Authentication", "[green]✓ OK[/green]", f"Source: {auth_status.source} ({auth_status.masked_token})")
        else:
            table.add_row("Authentication", "[yellow]! MISSING[/yellow]", "Run 'ghcontrib auth login' to authenticate")
            all_ok = False

        # 5. Network & GitHub GraphQL API
        if token:
            try:
                client = GitHubClient(token=token, timeout=8.0)
                rate_data = client.check_rate_limit()
                limit = rate_data.get("limit", 5000)
                remaining = rate_data.get("remaining", 0)
                table.add_row("GitHub GraphQL API", "[green]✓ CONNECTED[/green]", f"Rate Limit: {remaining:,} / {limit:,} remaining")
            except Exception as err:
                table.add_row("GitHub GraphQL API", "[red]✗ FAILED[/red]", str(err)[:80])
                all_ok = False
        else:
            table.add_row("GitHub GraphQL API", "[dim]SKIPPED[/dim]", "Requires token to test GraphQL rate limit")

        # 6. Terminal Color & Unicode Support
        width = get_terminal_width()
        color_ok = supports_color()
        truecolor_ok = supports_truecolor()
        unicode_ok = supports_unicode()

        term_details = f"Width: {width} cols | Color: {'Yes' if color_ok else 'No'} | TrueColor: {'Yes' if truecolor_ok else 'No'} | UTF-8: {'Yes' if unicode_ok else 'No'}"
        table.add_row("Terminal Display", "[green]✓ OK[/green]", term_details)

        # 7. Cache Directory
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            test_file = cache_dir / ".doctor_test"
            test_file.write_text("ok")
            test_file.unlink()
            table.add_row("Cache Directory", "[green]✓ WRITABLE[/green]", str(cache_dir))
        except Exception as err:
            table.add_row("Cache Directory", "[red]✗ PERMISSION ERROR[/red]", str(err))
            all_ok = False

        self.console.print(table)
        self.console.print("")

        if all_ok:
            self.console.print("[bold green]✓ All diagnostic checks passed successfully![/bold green]\n")
        else:
            self.console.print("[bold yellow]! Some checks reported issues. Follow the remediation steps above.[/bold yellow]\n")

        return all_ok
