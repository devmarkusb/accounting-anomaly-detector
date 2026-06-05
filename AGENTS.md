# AGENTS.md

Canonical instructions for AI agents working in this repository. Tool-specific files (`CLAUDE.md`, `.cursor/rules/`) are thin adapters that point here.

## Project overview

Python 3.11+ desktop app for importing monthly bank CSV exports, auditing transactions, and flagging amount anomalies per payee.

- **UI:** PySide6 (Qt), Fusion style
- **Storage:** SQLite at `~/.accounting_anomaly/data.db` (created at runtime)
- **Config:** Import profiles at `~/.accounting_anomaly/config.json`
- **Package manager:** [uv](https://docs.astral.sh/uv/) recommended; pip also documented
- **Layout:** `src/accounting_anomaly/` (hatchling wheel), tests in `tests/`

Transaction statuses: `pending`, `approved`, `anomaly`, `ignored`. Classification uses Welford online stats and a 2.5σ threshold (`core/anomaly.py`).

## Build commands

```bash
# Install editable with dev deps (verified)
uv pip install -e ".[dev]"

# Alternative (from README)
pip install -e ".[dev]"
```

```bash
# Run the app (verified entry points)
accounting-anomaly
python -m accounting_anomaly.main
```

No separate build artifact step; hatchling packages `src/accounting_anomaly` on install.

## Test commands

```bash
pytest tests/ -v
```

Headless Qt (CI and agents without a display):

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

Current suite: 14 tests covering CSV parsing and anomaly classification. No GUI integration tests.

## Formatting and linting

```bash
ruff check src tests
ruff format src tests          # apply
ruff format --check src tests  # CI check only
```

Ruff config (`pyproject.toml`): `line-length = 100`, `target-version = "py311"`, rules `E F I UP`, `E501` ignored.

No pre-commit hooks in this repo.

## Architecture and important directories

```
src/accounting_anomaly/
  main.py              # QApplication entry
  core/
    csv_parser.py      # CsvProfile, profile I/O, CSV parsing (no Qt)
    anomaly.py         # classify(); pure logic
  db/
    database.py        # SQLite schema, inserts, payee_stats, dedup by hash
  ui/
    main_window.py     # Primary window, import flow
    import_dialog.py   # Profile editor + preview
    transaction_table.py
tests/
  test_csv_parser.py
  test_anomaly.py
```

**Layering:** Keep `core/` and `db/` free of PySide6 imports so logic stays unit-testable. UI calls into db/core.

**CI:** `.github/workflows/ci.yml` — lint, format check, pytest on Ubuntu with system GL libs for PySide6.

## Coding conventions

- Type hints on public functions and methods
- `@dataclass` for structured config (`CsvProfile`)
- SQLite access via `_conn()` context manager; schema changes belong in `database.py` `_SCHEMA`
- Constants for business rules live next to logic (e.g. `ANOMALY_SIGMA`, `MIN_HISTORY` in `anomaly.py`)
- Match existing naming: snake_case modules, descriptive payee/transaction dict keys (`description`, `amount`, `status`)

## Testing expectations

- Add or update unit tests in `tests/` when changing `core/` or `db/` behavior
- Prefer testing pure functions (`classify`, CSV parse helpers) without Qt
- Do not add tests that embed real bank CSV data
- Run `pytest tests/ -v` and ruff before considering work complete

## Files and directories agents must not edit without explicit approval

- `.venv/`, `.ruff_cache/`, `.pytest_cache/`, `dist/`, `*.egg-info/`
- `.idea/` (local IDE settings)
- `~/.accounting_anomaly/` (user data and config on disk)
- `.github/workflows/ci.yml` (unless CI change is requested)
- `pyproject.toml` dependency or tool sections (unless dependency/tooling change is requested)
- Generated, vendored, or lock artifacts (no `uv.lock` today; do not add lockfiles unless asked)

## Security and privacy constraints

- Local-only app: no remote API, auth, or deployment surface in-repo
- Bank transactions are sensitive; never commit real CSV exports, account numbers, or `*.db` files
- Do not create or edit `.env`, credentials, or secrets files
- Schema/migration edits affect user databases; explain impact before changing `_SCHEMA` or hash/dedup logic

## Git and remote workflow

- **Never push without approval:** do not run `git push`, force-push, or equivalent publish flows (`gh` sync, etc.) unless the user explicitly requests it
- Create commits only when the user asks
- Local git operations (`status`, `diff`, `log`, staging) are fine

## Review checklist before final response

1. `ruff check src tests` and `ruff format --check src tests` pass
2. `pytest tests/ -v` passes (use `QT_QPA_PLATFORM=offscreen` if no display)
3. Core changes have corresponding unit tests
4. No real financial data added to the repo
5. Scope kept minimal; no unrelated refactors
6. User data paths (`~/.accounting_anomaly/`) unchanged unless explicitly requested
