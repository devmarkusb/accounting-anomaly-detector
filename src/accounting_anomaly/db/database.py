import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".accounting_anomaly" / "data.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    balance     REAL,
    month       TEXT    NOT NULL,
    account     TEXT    NOT NULL DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','approved','ignored','anomaly')),
    hash        TEXT    UNIQUE NOT NULL,
    imported_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payee_stats (
    description TEXT    PRIMARY KEY,
    count       INTEGER NOT NULL DEFAULT 0,
    mean        REAL    NOT NULL DEFAULT 0,
    m2          REAL    NOT NULL DEFAULT 0
);
"""
# m2 tracks sum of squared deviations via Welford's online algorithm


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript(_SCHEMA)


def make_hash(date: str, description: str, amount: float) -> str:
    raw = f"{date}\x00{description}\x00{amount:.6f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def get_payee_stats() -> dict[str, dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM payee_stats").fetchall()
    return {r["description"]: dict(r) for r in rows}


def _update_payee_stat(c: sqlite3.Connection, description: str, amount: float) -> None:
    row = c.execute(
        "SELECT count, mean, m2 FROM payee_stats WHERE description=?", (description,)
    ).fetchone()
    if row is None:
        c.execute(
            "INSERT INTO payee_stats(description, count, mean, m2) VALUES(?,1,?,0)",
            (description, amount),
        )
    else:
        n = row["count"] + 1
        mean, m2 = row["mean"], row["m2"]
        delta = amount - mean
        mean += delta / n
        m2 += delta * (amount - mean)
        c.execute(
            "UPDATE payee_stats SET count=?, mean=?, m2=? WHERE description=?",
            (n, mean, m2, description),
        )


def insert_transactions(rows: list[dict]) -> tuple[int, int]:
    """Returns (inserted, skipped_duplicates)."""
    inserted = skipped = 0
    with _conn() as c:
        for row in rows:
            h = make_hash(row["date"], row["description"], row["amount"])
            try:
                c.execute(
                    "INSERT INTO transactions"
                    "(date, description, amount, balance, month, account, status, hash)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (
                        row["date"],
                        row["description"],
                        row["amount"],
                        row.get("balance"),
                        row["month"],
                        row.get("account", ""),
                        row["status"],
                        h,
                    ),
                )
                if row["status"] == "approved":
                    _update_payee_stat(c, row["description"], row["amount"])
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return inserted, skipped


def get_transactions(*, month: str | None = None, status: str | None = None) -> list[dict]:
    with _conn() as c:
        q = "SELECT * FROM transactions WHERE 1=1"
        params: list = []
        if month:
            q += " AND month=?"
            params.append(month)
        if status:
            q += " AND status=?"
            params.append(status)
        q += " ORDER BY date DESC, id DESC"
        return [dict(r) for r in c.execute(q, params).fetchall()]


def update_status(tx_id: int, status: str) -> None:
    with _conn() as c:
        if status == "approved":
            row = c.execute(
                "SELECT description, amount FROM transactions WHERE id=?", (tx_id,)
            ).fetchone()
            if row:
                _update_payee_stat(c, row["description"], row["amount"])
        c.execute("UPDATE transactions SET status=? WHERE id=?", (status, tx_id))


def get_months() -> list[str]:
    with _conn() as c:
        rows = c.execute("SELECT DISTINCT month FROM transactions ORDER BY month DESC").fetchall()
    return [r[0] for r in rows]


def get_summary() -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT
                month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)  AS income,
                SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)  AS expenses,
                COUNT(*)                                            AS total,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status='anomaly' THEN 1 ELSE 0 END) AS anomalies
            FROM transactions
            WHERE status != 'ignored'
            GROUP BY month
            ORDER BY month DESC
        """).fetchall()
    return [dict(r) for r in rows]
