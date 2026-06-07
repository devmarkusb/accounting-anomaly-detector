import hashlib
import sqlite3
from pathlib import Path

from ..core.categories import is_saved_category
from ..core.payee import payee_identity

DB_PATH = Path.home() / ".accounting_anomaly" / "data.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    payee       TEXT    NOT NULL DEFAULT '',
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    balance     REAL,
    month       TEXT    NOT NULL,
    account     TEXT    NOT NULL DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','approved','ignored','anomaly')),
    category    TEXT    NOT NULL DEFAULT '',
    hash        TEXT    UNIQUE NOT NULL,
    imported_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payee_stats (
    description TEXT    PRIMARY KEY,
    count       INTEGER NOT NULL DEFAULT 0,
    mean        REAL    NOT NULL DEFAULT 0,
    m2          REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payee_categories (
    description TEXT    PRIMARY KEY,
    category    TEXT    NOT NULL
);
"""
# m2 tracks sum of squared deviations via Welford's online algorithm

_REVIEW_STATUSES = ("pending", "anomaly")


def _migrate(c: sqlite3.Connection) -> None:
    cols = {row[1] for row in c.execute("PRAGMA table_info(transactions)")}
    if "category" not in cols:
        c.execute("ALTER TABLE transactions ADD COLUMN category TEXT NOT NULL DEFAULT ''")
    if "payee" not in cols:
        c.execute("ALTER TABLE transactions ADD COLUMN payee TEXT NOT NULL DEFAULT ''")


def _ensure_schema(c: sqlite3.Connection) -> None:
    c.executescript(_SCHEMA)
    _migrate(c)


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(c)
    return c


def init_db() -> None:
    with _conn():
        pass


def clear_data() -> None:
    """Remove all transactions and learned stats/categories; keeps import profiles."""
    with _conn() as c:
        c.execute("DELETE FROM transactions")
        c.execute("DELETE FROM payee_stats")
        c.execute("DELETE FROM payee_categories")


def make_hash(date: str, description: str, amount: float) -> str:
    raw = f"{date}\x00{description}\x00{amount:.6f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def get_payee_stats() -> dict[str, dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM payee_stats").fetchall()
    return {r["description"]: dict(r) for r in rows}


def get_payee_categories() -> dict[str, str]:
    with _conn() as c:
        rows = c.execute("SELECT description, category FROM payee_categories").fetchall()
    return {r["description"]: r["category"] for r in rows}


def get_known_categories() -> list[str]:
    """Distinct user-saved category labels (not auto-filled purpose text)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT category FROM payee_categories ORDER BY category"
        ).fetchall()
    return [r[0] for r in rows]


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


def _save_payee_category(
    c: sqlite3.Connection, identity: str, category: str, *, purpose: str
) -> None:
    if not is_saved_category(purpose, category):
        return
    c.execute(
        """
        INSERT INTO payee_categories(description, category) VALUES(?,?)
        ON CONFLICT(description) DO UPDATE SET category=excluded.category
        """,
        (identity, category),
    )


def insert_transactions(rows: list[dict]) -> tuple[int, int]:
    """Returns (inserted, skipped_duplicates)."""
    inserted = skipped = 0
    with _conn() as c:
        for row in rows:
            h = make_hash(row["date"], row["description"], row["amount"])
            try:
                identity = payee_identity(row)
                c.execute(
                    "INSERT INTO transactions"
                    "(date, payee, description, amount, balance, month, account, status, category, hash)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        row["date"],
                        row.get("payee", ""),
                        row["description"],
                        row["amount"],
                        row.get("balance"),
                        row["month"],
                        row.get("account", ""),
                        row["status"],
                        row.get("category", ""),
                        h,
                    ),
                )
                if row["status"] == "approved":
                    _update_payee_stat(c, identity, row["amount"])
                category = row.get("category", "")
                if category:
                    _save_payee_category(c, identity, category, purpose=row["description"])
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


def get_review_queue() -> list[dict]:
    """Pending and anomaly transactions, oldest month first."""
    placeholders = ",".join("?" * len(_REVIEW_STATUSES))
    with _conn() as c:
        rows = c.execute(
            f"""
            SELECT * FROM transactions
            WHERE status IN ({placeholders})
            ORDER BY month ASC, date ASC, id ASC
            """,
            _REVIEW_STATUSES,
        ).fetchall()
    return [dict(r) for r in rows]


def update_status(tx_id: int, status: str) -> None:
    with _conn() as c:
        if status == "approved":
            row = c.execute(
                "SELECT payee, description, amount FROM transactions WHERE id=?", (tx_id,)
            ).fetchone()
            if row:
                _update_payee_stat(c, payee_identity(dict(row)), row["amount"])
        c.execute("UPDATE transactions SET status=? WHERE id=?", (status, tx_id))


def update_review(tx_id: int, status: str, category: str) -> None:
    """Apply review decision: status, optional category, and learned payee mapping."""
    with _conn() as c:
        row = c.execute(
            "SELECT payee, description, amount FROM transactions WHERE id=?", (tx_id,)
        ).fetchone()
        if row is None:
            return
        identity = payee_identity(dict(row))
        c.execute(
            "UPDATE transactions SET status=?, category=? WHERE id=?",
            (status, category, tx_id),
        )
        _save_payee_category(c, identity, category, purpose=row["description"])
        if status == "approved":
            _update_payee_stat(c, identity, row["amount"])


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
