# Accounting Anomaly Detector

[![CI](https://github.com/devmarkusb/accounting-anomaly-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/devmarkusb/accounting-anomaly-detector/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-orange)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Desktop app for importing monthly bank CSV exports, auditing transactions, and detecting anomalies automatically.

## How it works

1. Import your bank's CSV export each month (**Ctrl+I**)
2. New payees land as `pending` (verify they are legitimate); known payees with unusual amounts become `anomaly`
3. Walk through the **review queue** month by month (**Ctrl+R**) — assign a status and category to each entry
4. Categories are learned per payee and pre-filled on the next import
5. Over time, recurring payees with typical amounts are auto-approved — you review less each month

**Transaction statuses:**

| Status | Meaning |
|--------|---------|
| `pending` | New or unknown payee — needs your review (potentially unwanted) |
| `approved` | Known payee with a typical amount |
| `anomaly` | Known payee but amount is an outlier (>2.5σ from mean) |
| `ignored` | Excluded from reporting (e.g. transfers between own accounts) |

**Review shortcuts** (in review dialog): **A** approve, **I** ignore, **X** anomaly.

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
5. Click **OK** to import — if anything needs review, you'll be prompted to start the guided walkthrough

Profiles are saved to `~/.accounting_anomaly/config.json` — configure once per bank.

## Data

| Path | Contents |
|------|----------|
| `~/.accounting_anomaly/data.db` | Transactions, payee stats, learned categories |
| `~/.accounting_anomaly/config.json` | Import profiles |

Duplicate detection: re-importing the same CSV is safe; duplicates are skipped.

**Reset transaction data** (keeps import profiles):

```bash
rm -f ~/.accounting_anomaly/data.db ~/.accounting_anomaly/data.db-wal ~/.accounting_anomaly/data.db-shm
```

Or from Python: `accounting_anomaly.db.clear_data()`.
