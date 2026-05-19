import csv
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".accounting_anomaly" / "config.json"


@dataclass
class CsvProfile:
    name: str = "Default"
    delimiter: str = ";"
    decimal: str = ","
    thousands: str = "."
    skip_rows: int = 1
    date_col: int = 0
    date_format: str = "%d.%m.%Y"
    description_col: int = 1
    amount_col: int = 2
    balance_col: int = -1  # -1 = not present
    account: str = ""
    encoding: str = "utf-8-sig"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CsvProfile":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


def load_profiles() -> list[CsvProfile]:
    if not CONFIG_PATH.exists():
        return [CsvProfile()]
    data = json.loads(CONFIG_PATH.read_text())
    profiles = [CsvProfile.from_dict(p) for p in data.get("profiles", [])]
    return profiles or [CsvProfile()]


def save_profiles(profiles: list[CsvProfile]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"profiles": [p.to_dict() for p in profiles]}, indent=2))


def parse_amount(value: str, decimal: str, thousands: str) -> float:
    cleaned = value.strip()
    if thousands:
        cleaned = cleaned.replace(thousands, "")
    cleaned = cleaned.replace(decimal, ".")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return float(cleaned)


def read_raw(path: Path, profile: CsvProfile) -> tuple[list[str], list[list[str]]]:
    """Returns (header_row, data_rows) for preview; header_row may be empty."""
    text = path.read_text(encoding=profile.encoding, errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=profile.delimiter)
    all_rows = list(reader)
    if profile.skip_rows > 0 and len(all_rows) >= profile.skip_rows:
        header = all_rows[profile.skip_rows - 1]
        data = all_rows[profile.skip_rows :]
    else:
        header = []
        data = all_rows
    return header, data


def parse_csv(path: Path, profile: CsvProfile) -> list[dict]:
    _, rows = read_raw(path, profile)
    transactions = []
    for row in rows:
        if not row or all(c.strip() == "" for c in row):
            continue
        try:
            date_str = row[profile.date_col].strip()
            dt = datetime.strptime(date_str, profile.date_format)
            description = row[profile.description_col].strip()
            if not description:
                continue
            amount = parse_amount(row[profile.amount_col], profile.decimal, profile.thousands)
            balance: float | None = None
            if profile.balance_col >= 0:
                try:
                    balance = parse_amount(
                        row[profile.balance_col], profile.decimal, profile.thousands
                    )
                except (ValueError, IndexError):
                    pass
            transactions.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "description": description,
                    "amount": amount,
                    "balance": balance,
                    "month": dt.strftime("%Y-%m"),
                    "account": profile.account,
                    "status": "pending",
                }
            )
        except (ValueError, IndexError):
            continue
    return transactions
