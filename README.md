# Accounting Anomaly Detector

Desktop app for importing monthly bank CSV exports, auditing transactions, and detecting anomalies automatically.

## How it works

1. Import your bank's CSV export each month
2. New payees and unusual amounts are flagged automatically
3. Right-click to approve, ignore, or mark as anomaly
4. Over time, more transactions are auto-approved — only genuine anomalies need review

**Transaction statuses:**

| Status | Meaning |
|--------|---------|
| `pending` | New payee or insufficient history — needs review |
| `approved` | Known payee with a typical amount |
| `anomaly` | Known payee but amount is an outlier (>2.5σ from mean) |
| `ignored` | Excluded from reporting (e.g. transfers between own accounts) |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```bash
# With uv (recommended)
uv pip install -e ".[dev]"

# With pip
pip install -e ".[dev]"
```

## Run

```bash
accounting-anomaly

# or
python -m accounting_anomaly.main
```

## Test

```bash
pytest tests/ -v
```

## Lint / format

```bash
ruff check src tests
ruff format src tests
```

## Import a CSV

1. Press **Ctrl+I** or click **Import CSV**
2. Browse to your bank's CSV export
3. Configure the import profile (column indices, date format, delimiter, decimal separator)
4. Click **Preview** to verify parsing looks correct
5. Click **OK** to import

Profiles are saved to `~/.accounting_anomaly/config.json` — configure once per bank.

## Data

All data is stored locally in `~/.accounting_anomaly/data.db` (SQLite).
Duplicate detection: re-importing the same CSV is safe, duplicates are skipped.
