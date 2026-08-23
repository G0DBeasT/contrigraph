# Contrigraph Requirements Specification

## 1. Executive Summary
Contrigraph is a production-grade terminal application designed for Fedora Linux (and portable across POSIX/Windows) that fetches, computes, and renders GitHub contribution calendars with activity metrics and streaks directly within terminal emulators.

---

## 2. Functional Requirements (FR)

- **FR-1: Setup & Initialization**:
  - Command: `ghcontrib setup`
  - Prompts for GitHub username and contact email.
  - Creates OS-compliant configuration file without asking again on subsequent runs.
  
- **FR-2: Authentication & Token Management**:
  - Commands: `ghcontrib auth login`, `ghcontrib auth status`, `ghcontrib auth logout`.
  - Securely accepts GitHub Personal Access Token (PAT) via masked input.
  - Auto-discovers token from environment variable (`GITHUB_TOKEN`, `GH_TOKEN`) or GitHub CLI (`gh auth token`) if available.
  - Verifies token validity against GitHub API immediately.
  - Stores credentials with strict file permissions (`0600`).

- **FR-3: GitHub Contribution Data Retrieval**:
  - Fetches authentic contribution calendar via GitHub GraphQL API v4.
  - Supports query by year (e.g. `ghcontrib show --year 2025` or `--year 2026`) or default (past 12 months / current year).
  - Handles pagination, rate limiting (5000 pts/hr), HTTP timeouts, and error responses cleanly.

- **FR-4: Data Normalization & Density Calculation**:
  - Normalizes calendar days into standard 7-day columns (Sunday-Saturday or Monday-Sunday).
  - Handles leap years, future dates, missing dates, and year boundaries.
  - Maps counts into 5 density tiers (`0`: None, `1`: Low, `2`: Medium-Low, `3`: Medium-High, `4`: High).
  - Supports both GitHub official quartile levels and adaptive quartile calculation.

- **FR-5: Terminal Rendering**:
  - Primary view: 7x53 contribution matrix with month headers (Jan..Dec) and weekday labels (Mon, Wed, Fri).
  - Visual blocks: High-definition ANSI true-color green squares (`■` or `█`) with fallback to ASCII (`.`, `o`, `O`, `#`, `@`) or unicode blocks (`░`, `▒`, `▓`, `█`).
  - Adaptive responsiveness: Dynamically splits into half-year blocks (Jan-Jun, Jul-Dec) when terminal width is below 110 columns.
  - No-color (`--no-color` / `NO_COLOR=1`) and pure ASCII (`--ascii`) modes.

- **FR-6: Activity Statistics Engine**:
  - Computes exact metrics:
    - Total contributions in period.
    - Current streak (consecutive active days up to today).
    - Longest streak in year/period.
    - Most active day of the week and date with maximum contributions.
    - Average daily and weekly contributions.
    - Active days vs inactive days ratio.
  - Available via default view or dedicated `ghcontrib stats`.

- **FR-7: Local Cache & Performance**:
  - Stores queried data in `$XDG_CACHE_HOME/contrigraph/` with expiration TTL (default 4 hours for current year, immutable for past years).
  - Command `ghcontrib refresh` forces immediate remote fetch and cache update.
  - Execution from cache is near-instant (< 20ms).

- **FR-8: Doctor & System Diagnostics**:
  - Command: `ghcontrib doctor`
  - Validates Python runtime, XDG directories, configuration, auth status, API connectivity, rate limit balance, terminal width, TrueColor support, and cache status.

---

## 3. Non-Functional Requirements (NFR)

- **NFR-1: Performance**:
  - Warm execution (from cache): < 50ms.
  - Cold execution (network fetch): < 1.5s on typical broadband.
  
- **NFR-2: Security & Privacy**:
  - Credentials stored in isolated `auth.json` with permissions restricted to owner (`0600`).
  - API responses sanitized against ANSI escape injection before rendering.
  - No secrets logged or printed in terminal output or stack traces.

- **NFR-3: Reliability & Error Handling**:
  - Zero unhandled Python tracebacks in normal user execution.
  - Clear, user-actionable error messages with troubleshooting advice.
  - Detailed diagnostic trace available when invoked with `--verbose` / `-v`.

- **NFR-4: Portability & Cross-Platform Architecture**:
  - Primary OS: Fedora Linux 39/40/41+.
  - Clean abstraction layers for path resolution, terminal detection, and credential storage to ensure seamless operation on Ubuntu, Arch, macOS, and Windows.

- **NFR-5: Testability**:
  - 100% mocked offline testing for API, data normalizer, stats engine, and renderer.
  - High unit and integration test coverage across all subsystems.
