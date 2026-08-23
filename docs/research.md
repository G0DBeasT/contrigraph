# Contrigraph Technical Research Document

## 1. Overview
This document compiles the technical findings and engineering research supporting the design and implementation of **Contrigraph (`ghcontrib`)**—a high-fidelity GitHub contribution calendar and activity visualizer tailored for the Fedora Linux terminal and modern POSIX/cross-platform terminals.

---

## 2. GitHub API Investigation

### 2.1 API Options Comparison
GitHub provides two primary APIs for querying user information:
1. **GitHub REST API (v3)**:
   - Endpoint `/users/{username}/events` only returns the last 90 days of public activity (up to 300 events). It does not provide historical daily contribution totals or private contribution rollups without intensive pagination and custom event reduction.
2. **GitHub GraphQL API (v4)**:
   - Endpoint: `https://api.github.com/graphql`
   - Exposes `user(login: $username) { contributionsCollection(from: $from, to: $to) { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount contributionLevel weekday } } } } }`
   - Provides exact 1-year contribution matrix, daily counts, GitHub official density levels (`NONE`, `FIRST_QUARTILE`, `SECOND_QUARTILE`, `THIRD_QUARTILE`, `FOURTH_QUARTILE`), and total contributions.
   - Accurately captures commits, PRs, issues, code reviews, and optionally private contributions if authorized with `read:user` or `repo` scope.

### 2.2 GraphQL Query Specification
```graphql
query GetContributionCalendar($username: String!, $from: DateTime, $to: DateTime) {
  user(login: $username) {
    name
    login
    avatarUrl
    createdAt
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
            weekday
          }
        }
        months {
          name
          year
          firstDay
          totalWeeks
        }
      }
    }
  }
}
```

### 2.3 Rate Limits & Quotas
- **GraphQL Rate Limit**: 5,000 points per hour for authenticated requests. Each contribution calendar query costs 1 point.
- **Unauthenticated REST**: 60 requests per hour (GraphQL requires authentication).
- **Public Fallback**: For unauthenticated queries, official public GraphQL requires a token; fallback mechanism can query public contribution stats or guide the user through personal token setup.

### 2.4 Timezone & Date/Time Handling
- GitHub contribution calendars are calculated with respect to UTC boundaries or the user's localized contribution day window.
- The GraphQL API accepts `from` and `to` ISO 8601 strings (e.g., `2026-01-01T00:00:00Z` to `2026-12-31T23:59:59Z`).
- Leap year handling: 2024 and 2028 contain 366 days (53 calendar weeks). Data normalizers must handle arbitrary week counts (52 to 54 weeks).

---

## 3. Terminal Rendering & Formatting Research

### 3.1 Terminal Capabilities on Fedora
- Fedora default terminal (`gnome-terminal`, `ptyxis`, `konsole`, `alacritty`, `foot`, `kitty`) supports TrueColor (24-bit RGB) and UTF-8 by default (`LANG=en_US.UTF-8`, `COLORTERM=truecolor`).
- Unicode block characters widely supported in modern fonts (Fira Code, JetBrains Mono, DejaVu Sans Mono, Noto Sans Mono):
  - Full Block: `█` (`\u2588`)
  - Medium/Light Blocks: `▓` (`\u2593`), `▒` (`\u2592`), `░` (`\u2591`)
  - Lower blocks / squares: `■` (`\u25a0`), `▪` (`\u25aa`), `•` (`\u2022`), `⬝` (`\u2b1d`)
- High-contrast 256-color and 24-bit TrueColor Green Palettes:
  - Standard GitHub Green Theme:
    - Level 0 (Empty): `#161b22` / `dim grey` (or `·` / `░`)
    - Level 1 (Low): `#0e4429` / ANSI 28 / `green`
    - Level 2 (Medium-Low): `#006d32` / ANSI 34
    - Level 3 (Medium-High): `#26a641` / ANSI 40
    - Level 4 (High): `#39d353` / ANSI 46 / `bright_green`
- High-contrast / Colorblind / Dark / Light themes:
  - Accessible via configurable themes (e.g., `github-dark`, `github-light`, `monochrome`, `halloween`, `emerald`).

### 3.2 Terminal Width Constraints
- A full 53-week year rendered horizontally requires:
  - Weekday label (4 chars, e.g. `Mon `) + (53 weeks * 2 chars) = ~110 columns.
  - If terminal width < 110 columns (e.g., 80x24 standard terminal):
    - Layout strategy: Split into 6-month half-year views, or condensed 1-char per week mode (`█` instead of `█ `), or wrap months gracefully.
- Responsive layout engine dynamically queries `shutil.get_terminal_size()`.

---

## 4. Authentication and Credential Management

### 4.1 Token Types
1. **GitHub Fine-Grained Personal Access Tokens (PAT)**:
   - Permissions needed: `Account permissions -> Public data (read-only)` or `Metadata (read-only)` for public profile; `Profile -> Read` for private counts.
2. **GitHub Classic Personal Access Tokens (PAT)**:
   - Permissions needed: `read:user` (optional, for private contributions count).
3. **GitHub CLI (`gh`) Integration**:
   - If user has `gh` installed and authenticated on Fedora (`gh auth token`), Contrigraph can automatically detect and reuse the token if authorized.
4. **Interactive Setup / Secure File Storage**:
   - Store credentials in `~/.config/contrigraph/auth.json` (or OS keychain via secretstorage/keyring when available) with strict POSIX permissions `0600` (`-rw-------`).

### 4.2 Security Best Practices
- Never store tokens in world-readable files.
- Mask tokens when typed (`getpass`) and in log output.
- Clean separation between non-sensitive user profile preferences (`config.json`) and authentication credentials (`auth.json`).

---

## 5. Storage and Cross-Platform Conventions

### 5.1 Linux / Fedora (XDG Specification)
- Config: `$XDG_CONFIG_HOME/contrigraph` (defaults to `~/.config/contrigraph`)
- Cache: `$XDG_CACHE_HOME/contrigraph` (defaults to `~/.cache/contrigraph`)
- Data: `$XDG_DATA_HOME/contrigraph` (defaults to `~/.local/share/contrigraph`)

### 5.2 macOS & Windows Extensibility
- macOS: `~/Library/Application Support/contrigraph` and `~/Library/Caches/contrigraph`
- Windows: `%APPDATA%\contrigraph` and `%LOCALAPPDATA%\contrigraph`
- Implemented via a unified `PlatformPathManager` abstraction.
