# Contrigraph Supervisor Final Engineering Report

## 1. Project Overview
**Contrigraph (`ghcontrib` / `contrigraph` / `github-contrib`)** is a production-grade command-line application built primarily for **Fedora Linux** (and cross-platform ready for Linux, macOS, and Windows) that retrieves authentic GitHub contribution calendar activity via the official GitHub GraphQL API v4 and renders high-fidelity contribution graphs, streak metrics, and activity insights directly in the terminal emulator.

---

## 2. System Architecture

```
User Terminal Command (e.g. ghcontrib show --year 2026)
                        │
                        ▼
         ┌───────────────────────────────┐
         │      contrigraph.cli.main     │
         │   (Argparse + Rich Handler)   │
         └──────────────┬────────────────┘
                        │
                        ▼
         ┌───────────────────────────────┐
         │     Configuration & Auth      │
         │  (ConfigManager / AuthManager)│
         └──────────────┬────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│  Cache Manager   │ (Miss)   │  GitHub Client   │
│  (XDG JSON TTL)  ├─────────►│  (GraphQL API)   │
└────────┬─────────┘          └────────┬─────────┘
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
         ┌───────────────────────────────┐
         │     ContributionNormalizer    │
         │   (Domain Models & Density)   │
         └──────────────┬────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│Statistics Engine │          │Calendar Renderer │
│(Streaks, Averages│          │ (Rich TrueColor /│
│  & Peak Analysis)│          │  ASCII / Themes) │
└────────┬─────────┘          └────────┬─────────┘
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
              Rendered Terminal UI
```

---

## 3. Technology Choices and Rationale

1. **Python 3.10+**:
   - Standard runtime available on modern Fedora Linux (`python3.14`).
   - Zero compilation overhead for developers.
   - Clean packaging via standard `pyproject.toml` (`setuptools.build_meta`).

2. **Rich**:
   - Industry standard for modern terminal styling, TrueColor rendering, ANSI tables, and formatted alerts.
   - Automatic terminal width and color capability query.

3. **HTTPX & Standard Library**:
   - Modern HTTP client supporting connection pooling, timeouts, and GraphQL JSON communication with GitHub.

4. **Argparse**:
   - Standard library command parser providing zero-overhead, highly customizable subcommands, help formatting, and flag routing without extra fragile dependencies.

---

## 4. Agent Workflow & Subsystems

1. **Supervisor Agent**: Coordinated the phased lifecycle from Phase 0 to Phase 35, tracking state machine transitions and verifying exit criteria before phase advancement.
2. **Requirements Analyst**: Formulated functional and non-functional requirements in `docs/requirements.md`.
3. **Research Agent**: Investigated GraphQL schema, API rate limits, terminal rendering conventions, and POSIX permissions in `docs/research.md`.
4. **Architecture Agent**: Designed modular boundaries in `docs/architecture.md`.
5. **Testing Agent**: Developed 38 unit and integration tests across all packages.
6. **Code Review Agent**: Conducted multi-dimensional security and code review in `docs/code-review.md`.
7. **Documentation Agent**: Produced user-facing, thoroughly verified `README.md`.

---

## 5. Security Model
- **Credential Storage**: Authentication tokens are stored in `$XDG_CONFIG_HOME/contrigraph/auth.json` with strict POSIX permissions `0600` (`-rw-------`).
- **Token Masking**: Tokens are never printed in full (`ghp_***1234`).
- **Input Sanitization**: Remote API data is rendered safely via Rich text objects to prevent terminal escape injection.
- **No Passwords**: Authentication relies exclusively on GitHub Personal Access Tokens (PAT) or standard environment tokens (`GITHUB_TOKEN`).

---

## 6. Features & Capabilities

- **CLI Commands**:
  - `ghcontrib`: Default invocation, displays graph for configured user.
  - `ghcontrib setup`: First-time interactive or automated configuration.
  - `ghcontrib auth login | status | logout`: Token management.
  - `ghcontrib show [--year YEAR] [--theme THEME] [--format terminal|json|csv]`: Configurable viewing.
  - `ghcontrib stats`: Dedicated activity metrics table.
  - `ghcontrib refresh`: Force live refresh and update cache.
  - `ghcontrib config show | set | reset`: Preferences management.
  - `ghcontrib doctor`: System, network, token, and terminal diagnostics.
  - `ghcontrib version`: Version reporting.
- **Visual Themes**:
  - `github-dark` (Default GitHub TrueColor Green)
  - `github-light`
  - `emerald`
  - `halloween`
  - `unicode-blocks`
  - `ascii`
  - `monochrome`
- **Responsive Layout**:
  - Full width (>= 110 columns): Continuous 52/53-week view.
  - Narrow terminals (< 110 columns): Responsive half-year block view (Early & Later period) to prevent visual corruption.

---

## 7. Test Results
- **Framework**: `pytest`
- **Total Tests**: 38 passed
- **Duration**: ~1.3 seconds
- **Pass Rate**: 100%

---

## 8. Cross-Platform Plan & Future Roadmap
- **Fedora / Linux**: Complete and native (XDG Base Directory compliant).
- **macOS**: Path resolution points to `~/Library/Application Support/contrigraph` and `~/Library/Caches/contrigraph`.
- **Windows**: Path resolution points to `%APPDATA%\contrigraph` and `%LOCALAPPDATA%\contrigraph`.
- **Future Enhancements**:
  - User comparison mode (`ghcontrib compare user1 user2`).
  - Export to SVG / SVG badge generation.
  - Neovim and Tmux status line integrations.
