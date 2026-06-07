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
    payee_col: int = -1  # -1 = not present; stats/categories fall back to description
    payee_header: str = ""  # e.g. "Zahlungsempfänger"
    description_col: int = 1
    description_header: str = ""  # e.g. "Verwendungszweck"
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


def _header_aliases(names: str) -> set[str]:
    return {n.strip().lower() for n in names.replace("|", ",").split(",") if n.strip()}


def header_column_indices(header: list[str], names: str) -> list[int]:
    """All column indices whose header matches one of the comma/|‑separated aliases."""
    aliases = _header_aliases(names)
    if not aliases:
        return []
    return [i for i, h in enumerate(header) if h.strip().lower() in aliases]


def resolve_column_index(header: list[str], index: int, header_name: str) -> int:
    """Use header name when set and found, otherwise fall back to numeric index."""
    if header_name.strip():
        for i, h in enumerate(header):
            if h.strip().lower() == header_name.strip().lower():
                return i
    return index


def _cell_text(row: list[str], col: int) -> str:
    try:
        return row[col].strip()
    except IndexError:
        return ""


def _first_non_empty(row: list[str], cols: list[int]) -> str:
    for col in cols:
        text = _cell_text(row, col)
        if text:
            return text
    return ""


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
    header, rows = read_raw(path, profile)
    date_col = resolve_column_index(header, profile.date_col, "")
    desc_col = resolve_column_index(header, profile.description_col, profile.description_header)
    amount_col = resolve_column_index(header, profile.amount_col, "")
    balance_col = resolve_column_index(header, profile.balance_col, "")

    payee_cols = header_column_indices(header, profile.payee_header)
    if not payee_cols and profile.payee_col >= 0:
        payee_cols = [profile.payee_col]

    transactions = []
    for row in rows:
        if not row or all(c.strip() == "" for c in row):
            continue
        try:
            date_str = _cell_text(row, date_col)
            dt = datetime.strptime(date_str, profile.date_format)
            description = _cell_text(row, desc_col)
            payee = _first_non_empty(row, payee_cols)
            if not description and not payee:
                continue
            if not description:
                description = payee
            amount = parse_amount(_cell_text(row, amount_col), profile.decimal, profile.thousands)
            balance: float | None = None
            if balance_col >= 0:
                try:
                    balance = parse_amount(
                        _cell_text(row, balance_col), profile.decimal, profile.thousands
                    )
                except ValueError:
                    pass
            transactions.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "payee": payee,
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
