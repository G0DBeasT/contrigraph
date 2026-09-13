"""Doctor command to diagnose environment, auth, network, and terminal health."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from contrigraph.api.client import GitHubClient
from contrigraph.auth.manager import AuthManager
from contrigraph.config.manager import ConfigManager
from contrigraph.utils.platform import (
    PlatformPaths,
    TerminalCapabilities,
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

    @staticmethod
    def _detect_os_description() -> str:
        """Detect detailed operating system, distribution name, or Termux environment."""
        # 1. Check for Termux environment
        termux_ver = os.environ.get("TERMUX_VERSION")
        prefix = os.environ.get("PREFIX", "")
        if termux_ver or "com.termux" in prefix:
            ver_str = f" v{termux_ver}" if termux_ver else ""
            return f"Android/Termux{ver_str}"

        # 2. Check for Linux distributions
        if sys.platform.startswith("linux"):
            try:
                if hasattr(platform, "freedesktop_os_release"):
                    info = platform.freedesktop_os_release()
                    pretty = info.get("PRETTY_NAME") or info.get("NAME")
                    if pretty:
                        return f"Linux ({pretty})"
            except Exception:
                pass

            try:
                os_release = Path("/etc/os-release")
                if os_release.exists():
                    for line in os_release.read_text(encoding="utf-8").splitlines():
                        if line.startswith("PRETTY_NAME="):
                            val = line.split("=", 1)[1].strip("\"'")
                            if val:
                                return f"Linux ({val})"
                        elif line.startswith("NAME=") and not line.startswith("PRETTY_NAME="):
                            val = line.split("=", 1)[1].strip("\"'")
                            if val:
                                return f"Linux ({val})"
            except Exception:
                pass

            return "Linux (Generic)"

        elif sys.platform == "darwin":
            ver = platform.mac_ver()[0]
            return f"macOS {ver}" if ver else "macOS"

        elif sys.platform == "win32":
            rel = platform.release()
            return f"Windows {rel}" if rel else "Windows"

        return sys.platform

    @staticmethod
    def _check_gh_cli() -> tuple[str, str]:
        """Check presence and version of GitHub CLI (gh)."""
        gh_path = shutil.which("gh")
        if not gh_path:
            return "[dim]NOT FOUND[/dim]", "(Optional) Used for auto-detecting GitHub credentials"

        gh_ver = ""
        try:
            res = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                first_line = res.stdout.strip().splitlines()[0]
                gh_ver = first_line
        except Exception:
            pass

        details = f"{gh_ver} ({gh_path})" if gh_ver else f"Installed ({gh_path})"
        return "[green]✓ INSTALLED[/green]", details

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
        os_desc = self._detect_os_description()
        table.add_row("OS Platform", "[green]✓ OK[/green]", f"{os_desc} (Config: {config_dir})")

        # 3. GitHub CLI (gh)
        gh_status, gh_details = self._check_gh_cli()
        table.add_row("GitHub CLI (gh)", gh_status, gh_details)

        # 4. Configuration
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

        # 5. Authentication & Credentials
        auth_status = self.auth_mgr.get_auth_status()
        token = self.auth_mgr.get_token()

        if auth_status.is_authenticated and token:
            table.add_row("Authentication", "[green]✓ OK[/green]", f"Source: {auth_status.source} ({auth_status.masked_token})")
        else:
            table.add_row("Authentication", "[yellow]! MISSING[/yellow]", "Run 'ghcontrib auth login' to authenticate")
            all_ok = False

        # 6. Network & GitHub API
        if token:
            try:
                client = GitHubClient(token=token, timeout=8.0)
                rate_data = client.check_rate_limit()
                limit = rate_data.get("limit", 5000)
                remaining = rate_data.get("remaining", 0)
                table.add_row("GitHub API", "[green]✓ CONNECTED[/green]", f"Rate Limit: {remaining:,} / {limit:,} remaining")
            except Exception as err:
                table.add_row("GitHub API", "[red]✗ FAILED[/red]", str(err)[:80])
                all_ok = False
        else:
            try:
                with httpx.Client(timeout=5.0) as http_client:
                    res = http_client.get(
                        "https://api.github.com/zen",
                        headers={"User-Agent": "contrigraph-doctor/0.1.0"},
                    )
                    if res.status_code == 200:
                        zen_msg = res.text.strip().replace("\n", " ")
                        table.add_row("GitHub API (HTTPS)", "[green]✓ REACHABLE[/green]", f"Connected to api.github.com (Zen: \"{zen_msg}\")")
                    else:
                        table.add_row("GitHub API (HTTPS)", "[yellow]! HTTP ERROR[/yellow]", f"api.github.com returned HTTP {res.status_code}")
            except Exception as err:
                table.add_row("GitHub API (HTTPS)", "[red]✗ UNREACHABLE[/red]", f"Cannot connect to api.github.com: {err}"[:80])
                all_ok = False

        # 7. Terminal Display & Dimensions
        caps = TerminalCapabilities.detect(console=self.console)
        if caps.width < 58:
            term_status = "[yellow]! NARROW[/yellow]"
            term_details = (
                f"Width: {caps.width} cols (< 58 cols; graph columns may wrap) | "
                f"Color: {'Yes' if caps.supports_color else 'No'} | "
                f"TrueColor: {'Yes' if caps.supports_truecolor else 'No'} | "
                f"UTF-8: {'Yes' if caps.supports_unicode else 'No'}"
            )
        else:
            term_status = "[green]✓ OK[/green]"
            term_details = (
                f"Width: {caps.width} cols | Color: {'Yes' if caps.supports_color else 'No'} | "
                f"TrueColor: {'Yes' if caps.supports_truecolor else 'No'} | "
                f"UTF-8: {'Yes' if caps.supports_unicode else 'No'}"
            )
        table.add_row("Terminal Display", term_status, term_details)

        # 8. Cache Directory
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
