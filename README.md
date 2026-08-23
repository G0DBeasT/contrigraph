# Contrigraph (`ghcontrib`)

> **GitHub Contribution Graph CLI for Fedora Terminal and Modern POSIX Systems**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Fedora%20%7C%20Linux%20%7C%20macOS%20%7C%20Windows-brightgreen.svg)](#cross-platform-architecture)

**Contrigraph** brings the iconic GitHub contribution calendar directly into your terminal. Designed natively for **Fedora Linux** and portable across modern terminal emulators, it renders 5-level green density blocks, computes streak statistics, caches data locally using XDG standards, and offers secure credential management.

```text
╭──────────────── GitHub Contributions • @octocat (2026) ────────────────╮
│ 487 contributions in this period (7 day current streak, 19 day longest)│
╰────────────────────────────────────────────────────────────────────────╯
    Jan      Feb      Mar      Apr      May      Jun      Jul      Aug      Sep      Oct      Nov      Dec
Mon  ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■
     ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■
Wed  ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■
     ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■
Fri  ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■
     ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■
     ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■ ■

      Less  ■ ■ ■ ■ ■  More

                         Activity Insights
  Metric               Value             Metric                Value
  ──────────────────────────────────────────────────────────────────────────
  Total Contributions  487               Active Days           189 / 365 (51.8%)
  Current Streak       7 days            Longest Streak        19 days
  Daily Average        1.33 / day        Weekly Average        9.34 / week
  Peak Activity Day    2026-03-03 (10)   Most Active Weekday   Wednesday
  Commits              312               Pull Requests         80
  Issues               45                Code Reviews          50
```

---

## Features

- 🟢 **High-Fidelity GitHub Graph**: Authentic 5-tier density calculation matching GitHub's official quartiles.
- ⚡ **Blazing Fast Local Cache**: Warm renders execute in < 20ms using structured XDG JSON storage.
- 📊 **Comprehensive Activity Insights**: Current streak, longest streak, active days, weekday activity distributions, and commit/PR/issue breakdowns.
- 🎨 **Multiple Color Themes**: `github-dark` (TrueColor green), `github-light`, `emerald`, `halloween` (pumpkin orange), `unicode-blocks` (`░▒▓█`), `ascii` (`.oO#@`), and `monochrome`.
- 📐 **Responsive Terminal Layout**: Automatically detects terminal width and splits into clean half-year segments (Jan–Jun, Jul–Dec) on terminals narrower than 110 columns to prevent line-wrapping artifacts.
- 🔒 **Secure Token Storage**: Authentication tokens are isolated in `$XDG_CONFIG_HOME/contrigraph/auth.json` with strict POSIX permissions (`0600`).
- 🩺 **Built-in Doctor Diagnostic**: Run `ghcontrib doctor` to inspect Python runtime, token health, API rate limits, terminal color support, and cache status.
- 📦 **Zero-Config CLI Aliases**: Use `ghcontrib`, `contrigraph`, or `github-contrib`.

---

## Requirements

- **Operating System**: Fedora Linux 38/39/40/41+ (or any modern Linux, macOS, or Windows system)
- **Python**: Python 3.10 or newer
- **GitHub Account**: Public or private account
- **Network**: HTTPS access to `api.github.com`

---

## Installation

### Fedora Linux (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/example/contrigraph.git
cd contrigraph

# 2. Set up virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode
pip install -e .
```

After installation, the commands `ghcontrib`, `contrigraph`, and `github-contrib` will be available in your PATH.

---

## First-Time Setup

Run the interactive setup wizard:

```bash
ghcontrib setup
```

You will be prompted for:
1. **GitHub username**: Your GitHub handle (e.g. `torvalds` or `octocat`).
2. **Email address** *(optional)*: Stored locally as application metadata.
3. **Preferred theme** *(optional)*: Default is `github-dark`.

You can also run setup non-interactively in scripts:

```bash
ghcontrib setup --user octocat --email dev@example.com --theme emerald
```

Configuration is stored in `~/.config/contrigraph/config.json`.

---

## Authentication

Contrigraph uses the official **GitHub GraphQL API v4**. To authenticate:

### 1. Create a GitHub Personal Access Token (PAT)
1. Go to [GitHub Settings -> Tokens (Classic)](https://github.com/settings/tokens) or [Fine-grained tokens](https://github.com/settings/tokens?type=beta).
2. For public activity only, minimal scope (or no extra scopes) is required.
3. To include private contributions in your total count, check the `read:user` scope.

### 2. Log In Securely

```bash
ghcontrib auth login
```

Enter your token when prompted (input is masked for security). The token is verified against GitHub's API and saved with strict `0600` permissions.

You can also log in directly via argument:

```bash
ghcontrib auth login --token ghp_yourSecretTokenHere
```

### 3. Check Authentication Status

```bash
ghcontrib auth status
```

### 4. Log Out

```bash
ghcontrib auth logout
```

> **Note**: Contrigraph also automatically detects tokens from environment variables (`GITHUB_TOKEN`, `GH_TOKEN`) or the GitHub CLI (`gh auth token`) if available!

---

## Usage Guide

### Display Current Year Graph

```bash
ghcontrib
# or
ghcontrib show
```

### Display Graph for a Specific Year

```bash
ghcontrib show --year 2025
```

### View Activity Insights Only

```bash
ghcontrib stats
```

### Force Refresh Cache

```bash
ghcontrib refresh
```

### Choose Themes & Display Options

```bash
# TrueColor Emerald Theme
ghcontrib show --theme emerald

# Halloween Orange Theme
ghcontrib show --theme halloween

# Classic Unicode Shading Blocks (░ ▒ ▓ █)
ghcontrib show --theme unicode-blocks

# Plain ASCII Mode (for non-Unicode terminals)
ghcontrib show --ascii

# Monochrome / No Color
ghcontrib show --no-color

# Compact mode (graph only, no stats table)
ghcontrib show --compact
```

### Export Data (JSON & CSV)

```bash
# Export as JSON
ghcontrib show --format json > contributions.json

# Export as CSV
ghcontrib show --format csv > contributions.csv
```

### Run System Doctor

```bash
ghcontrib doctor
```

Output example:
```text
╭──────────────── Contrigraph System Doctor ────────────────╮
│ Category            Status        Details                 │
│ Python Version      ✓ OK          Python 3.14.7           │
│ OS Platform         ✓ OK          linux (~/.config/...)   │
│ Configuration       ✓ OK          User: @octocat          │
│ Authentication      ✓ OK          Source: file (ghp_***)  │
│ GitHub GraphQL API  ✓ CONNECTED   Rate Limit: 4,992/5,000 │
│ Terminal Display    ✓ OK          Width: 120 cols | TrueColor: Yes │
│ Cache Directory     ✓ WRITABLE    ~/.cache/contrigraph    │
╰───────────────────────────────────────────────────────────╯
```

### Manage Preferences

```bash
# View current configuration
ghcontrib config show

# Change theme
ghcontrib config set theme emerald

# Change cache TTL (hours)
ghcontrib config set cache_ttl_hours 6

# Reset configuration
ghcontrib config reset
```

---

## Architecture Overview

Contrigraph is built with strict separation of concerns across layered modules:

```text
CLI (argparse + rich)
    ↓
Application & Flow Control
    ↓
ConfigManager & AuthManager  <──>  CacheManager ($XDG_CACHE_HOME)
    ↓
GitHub GraphQL Client
    ↓
ContributionNormalizer (Domain Models & Density Engine)
    ↓
StatisticsEngine (Streaks & Analytics)
    ↓
CalendarRenderer (TrueColor ANSI, ASCII, JSON, CSV)
```

### Directory Structure

```text
contrigraph/
├── pyproject.toml              # Project packaging & dependencies
├── README.md                   # User guide & documentation
├── LICENSE                     # MIT License
├── docs/                       # Architecture, requirements, research
│   ├── architecture.md
│   ├── requirements.md
│   ├── research.md
│   ├── code-review.md
│   └── final-report.md
├── src/
│   └── contrigraph/
│       ├── __init__.py
│       ├── cli/                # Command line interface & doctor
│       │   ├── main.py
│       │   └── doctor.py
│       ├── api/                # GitHub GraphQL API client
│       │   └── client.py
│       ├── auth/               # Secure credential management
│       │   └── manager.py
│       ├── config/             # User settings management
│       │   └── manager.py
│       ├── models/             # Domain models (Calendar, Day, Week, Stats)
│       │   └── calendar.py
│       ├── data/               # Normalizer & density quartile engine
│       │   ├── normalizer.py
│       │   └── density.py
│       ├── statistics/         # Streaks & activity calculations
│       │   └── engine.py
│       ├── cache/              # XDG JSON caching with TTL
│       │   └── manager.py
│       ├── rendering/          # Terminal visualizer & themes
│       │   ├── renderer.py
│       │   └── themes.py
│       └── utils/              # Platform paths, permissions, error hierarchy
│           ├── platform.py
│           └── errors.py
└── tests/                      # 38 unit & integration tests
    ├── conftest.py
    ├── fixtures/
    ├── unit/
    └── integration/
```

---

## Troubleshooting

### 1. `GitHub token is invalid or expired`
**Fix**: Generate a new token at [GitHub Settings -> Tokens](https://github.com/settings/tokens) and run:
```bash
ghcontrib auth login
```

### 2. `GitHub API rate limit exceeded`
**Fix**: Unauthenticated requests are limited. Authenticate with a personal access token via:
```bash
ghcontrib auth login
```
This raises your limit to 5,000 GraphQL points per hour.

### 3. Unicode block characters render as `?` or boxes
**Fix**: If your terminal font lacks full block glyphs (`■`), use the ASCII fallback:
```bash
ghcontrib show --ascii
```
Or switch to a modern programming font such as *Fira Code*, *JetBrains Mono*, or *DejaVu Sans Mono*.

### 4. No colors appearing in terminal
**Fix**: Check if `NO_COLOR=1` is set in your environment, or ensure your terminal supports ANSI color. You can test terminal capabilities with:
```bash
ghcontrib doctor
```

---

## Testing

Run the full automated test suite:

```bash
pytest -v
```

---

## License

Contrigraph is released under the [MIT License](LICENSE).
