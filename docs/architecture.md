# Contrigraph Architecture Specification

## 1. Architectural Overview

Contrigraph is structured into layered, decoupled modules following clean architecture principles. No layer directly leaks raw HTTP or UI implementation details to other layers.

```
┌────────────────────────────────────────────────────────┐
│                   CLI Interface Layer                  │
│          (argparse, commands, error presentation)      │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Application Service                 │
│         (Orchestration, Session, Flow Control)         │
└──────┬────────────────────┬────────────────────┬───────┘
       │                    │                    │
┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
│Config & Auth│      │Cache Manager│      │GitHub Client│
│  (Storage)  │      │  (XDG JSON) │      │  (GraphQL)  │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                 │
                                          ┌──────▼──────┐
                                          │ Data Models │
                                          └──────┬──────┘
                                                 │
                             ┌───────────────────┴───────────────────┐
                             │                                       │
                      ┌──────▼──────┐                         ┌──────▼──────┐
                      │ Normalizer  │                         │ Statistics  │
                      │  & Density  │                         │   Engine    │
                      └──────┬──────┘                         └──────┬──────┘
                             │                                       │
                             └───────────────────┬───────────────────┘
                                                 │
                                          ┌──────▼──────┐
                                          │  Terminal   │
                                          │  Renderer   │
                                          │   (Rich)    │
                                          └─────────────┘
```

---

## 2. Module Specifications & Interfaces

### 2.1 Configuration & Authentication (`contrigraph.config` & `contrigraph.auth`)
- **`PlatformPaths`**: Resolves XDG paths on Linux/Fedora (`~/.config/contrigraph`, `~/.cache/contrigraph`) with fallback for macOS/Windows.
- **`ConfigManager`**: Manages non-sensitive user settings (`username`, `email`, `theme`, `default_year`, `cache_ttl_hours`).
- **`AuthManager`**: Manages GitHub tokens (`login`, `logout`, `get_token`, `validate_token`). Ensures filesystem permissions `0600` on credentials file.

### 2.2 GitHub API Client (`contrigraph.api`)
- **`GitHubClient`**: Handles authenticated requests to `https://api.github.com/graphql`.
- Features: Automatic retries for transient HTTP errors (502, 503, 504), timeout management, rate limit checking, token discovery (env/file/`gh`), and structured error mapping (`AuthError`, `RateLimitError`, `UserNotFoundError`, `NetworkError`).

### 2.3 Domain Models (`contrigraph.models`)
- **`ContributionDay`**: Immutable dataclass containing `date` (date), `count` (int), `level` (int 0-4), `weekday` (int 0-6).
- **`ContributionWeek`**: Dataclass containing `days: list[ContributionDay]`.
- **`ContributionMonth`**: Dataclass containing `name`, `year`, `first_week_idx`, `total_weeks`.
- **`ContributionCalendar`**: Complete model containing `username`, `year`, `from_date`, `to_date`, `total_contributions`, `weeks`, `months`.
- **`ContributionStats`**: Computed statistics dataclass containing `total_contributions`, `current_streak`, `longest_streak`, `active_days`, `average_per_day`, `average_per_week`, `max_day`, `max_count`, `most_active_weekday`, `most_active_month`.

### 2.4 Data Processing & Density (`contrigraph.data`)
- **`ContributionNormalizer`**: Transforms raw GraphQL calendar JSON into structured `ContributionCalendar`. Fills missing dates, handles leap years (366 days), sorts weeks chronologically, and establishes matrix grid alignment.
- **`DensityEngine`**: Maps contribution counts to 5 discrete density tiers (`0` to `4`) using GitHub official quartile data or adaptive histogram thresholding.

### 2.5 Statistics Engine (`contrigraph.statistics`)
- **`StatisticsEngine`**: Pure computational engine without external dependencies.
- Calculates exact streaks (consecutive days with contributions > 0 ending today or on the last recorded calendar day), all-time longest streaks, weekday distributions, and active day ratios.

### 2.6 Cache System (`contrigraph.cache`)
- **`CacheManager`**: Persists normalized `ContributionCalendar` as structured JSON under `$XDG_CACHE_HOME/contrigraph/`.
- Fast serialization and deserialization.
- Smart TTL: Cached data for the current year expires after configured TTL (default 4 hours), while completed past years (e.g. 2025 in 2026) are cached permanently unless `--clear-cache` or `refresh` is requested.

### 2.7 Terminal Rendering Engine (`contrigraph.rendering`)
- **`CalendarRenderer`**: Generates visual representations using Rich and ANSI escapes.
- **Adaptive Layout**:
  - Full width (>= 110 cols): Continuous 12-month horizontal display.
  - Narrow terminal (< 110 cols): Two 6-month blocks (Jan-Jun, Jul-Dec) or compact single-column rendering.
- **Themes**:
  - `github-dark` (default): TrueColor green `#161b22`, `#0e4429`, `#006d32`, `#26a641`, `#39d353` with `■`.
  - `github-light`: Light background TrueColor green.
  - `unicode-blocks`: Using `░`, `▒`, `▓`, `█`.
  - `ascii`: High-contrast characters `·`, `o`, `O`, `#`, `@` for dumb terminals or `--ascii`.
  - `no-color`: Monochrome density characters.

### 2.8 Diagnostic System (`contrigraph.cli.doctor`)
- Inspects and prints formatted status checks:
  1. Python runtime version (>= 3.10)
  2. Local configuration file validity
  3. GitHub authentication status and token scopes
  4. GitHub API connectivity and GraphQL rate limit remaining
  5. Terminal dimensions, TrueColor support, UTF-8 locale
  6. Cache directory read/write health

---

## 3. Error Handling Architecture

Custom exception hierarchy:
```text
ContrigraphError (Base)
├── ConfigurationError
│   ├── ConfigNotFoundError
│   └── InvalidConfigError
├── AuthenticationError
│   ├── MissingTokenError
│   ├── InvalidTokenError
│   └── ExpiredTokenError
├── APIError
│   ├── UserNotFoundError
│   ├── RateLimitExceededError
│   ├── NetworkError
│   └── GitHubServerError
└── RenderError
```

All CLI handlers catch `ContrigraphError` and format it using Rich alert panels with clear remediation commands (e.g., `Run: ghcontrib auth login`).

---

## 4. Cross-Platform Abstraction

Platform-specific logic is strictly isolated in `contrigraph.utils.platform`:
- POSIX/Linux file permissions (`0600`) safely ignored/adapted on Windows.
- Standard paths resolved via standard environment variables and OS conventions.
- Terminal color and size querying handled through unified wrapper.
