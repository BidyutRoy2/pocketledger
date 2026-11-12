"""SQLite storage for pocketledger.

One file (``ledger.db``) holds everything: accounts, transactions,
categorisation rules, budgets and balance snapshots. Schema is versioned
with a tiny migration table so later releases can evolve it safely.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL DEFAULT 'checking',
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,              -- ISO date YYYY-MM-DD
    amount_minor INTEGER NOT NULL,   -- cents; negative = money out
    payee TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Uncategorized',
    account_id INTEGER REFERENCES accounts(id),
    note TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    fingerprint TEXT NOT NULL UNIQUE -- dedupe key for imports
);

CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_payee ON transactions(payee);

CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,           -- case-insensitive substring on payee
    category TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern, category)
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    month TEXT NOT NULL,             -- YYYY-MM
    limit_minor INTEGER NOT NULL,    -- cents, money out
    UNIQUE(category, month)
);

CREATE TABLE IF NOT EXISTS balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    date TEXT NOT NULL,              -- ISO date of the snapshot
    balance_minor INTEGER NOT NULL,
    UNIQUE(account_id, date)
);
"""


@dataclass
class Transaction:
    id: int
    date: str
    amount_minor: int
    payee: str
    category: str
    account_id: int | None
    note: str
    source: str


def fingerprint(date: str, amount_minor: int, payee: str, account_id: int | None) -> str:
    """Stable dedupe key: same date + amount + payee + account = one row."""
    key = f"{date}|{amount_minor}|{payee.strip().lower()}|{account_id or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


class Store:
    """Thin wrapper around the ledger SQLite database."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(_SCHEMA)
        self.conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- accounts ---------------------------------------------------------
    def add_account(self, name: str, kind: str = "checking", currency: str = "USD") -> int:
        cur = self.conn.execute(
            "INSERT INTO accounts(name, kind, currency) VALUES (?, ?, ?)",
            (name.strip(), kind, currency.upper()),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_accounts(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
        )

    def get_account(self, name: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM accounts WHERE name = ?", (name.strip(),)
        ).fetchone()

    # -- transactions -----------------------------------------------------
    def add_transaction(
        self,
        date: str,
        amount_minor: int,
        payee: str,
        category: str = "Uncategorized",
        account_id: int | None = None,
        note: str = "",
        source: str = "manual",
    ) -> tuple[int, bool]:
        """Insert a transaction. Returns (row id, inserted?). Duplicates
        (same fingerprint) are skipped and reported as not inserted."""
        fp = fingerprint(date, amount_minor, payee, account_id)
        try:
            cur = self.conn.execute(
                """INSERT INTO transactions
                   (date, amount_minor, payee, category, account_id, note, source, fingerprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (date, amount_minor, payee.strip(), category.strip() or "Uncategorized",
                 account_id, note.strip(), source, fp),
            )
        except sqlite3.IntegrityError:
            return -1, False
        self.conn.commit()
        return cur.lastrowid, True

    def list_transactions(
        self,
        month: str | None = None,
        category: str | None = None,
        account_id: int | None = None,
        limit: int = 200,
    ) -> list[Transaction]:
        sql = "SELECT * FROM transactions WHERE 1=1"
        args: list = []
        if month:
            sql += " AND substr(date, 1, 7) = ?"
            args.append(month)
        if category:
            sql += " AND category = ?"
            args.append(category)
        if account_id is not None:
            sql += " AND account_id = ?"
            args.append(account_id)
        sql += " ORDER BY date DESC, id DESC LIMIT ?"
        args.append(limit)
        rows = self.conn.execute(sql, args).fetchall()
        return [self._row_to_tx(r) for r in rows]

    def count_transactions(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    def sum_by_category(self, month: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """SELECT category, COUNT(*) AS n, SUM(amount_minor) AS total
                   FROM transactions WHERE substr(date, 1, 7) = ?
                   GROUP BY category ORDER BY total ASC""",
                (month,),
            ).fetchall()
        )

    def month_totals(self, month: str) -> tuple[int, int]:
        row = self.conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN amount_minor > 0 THEN amount_minor ELSE 0 END), 0) AS income,
                 COALESCE(SUM(CASE WHEN amount_minor < 0 THEN -amount_minor ELSE 0 END), 0) AS spending
               FROM transactions WHERE substr(date, 1, 7) = ?""",
            (month,),
        ).fetchone()
        return row["income"], row["spending"]

    def uncategorized(self) -> list[Transaction]:
        rows = self.conn.execute(
            "SELECT * FROM transactions WHERE category = 'Uncategorized' ORDER BY date DESC"
        ).fetchall()
        return [self._row_to_tx(r) for r in rows]

    def set_category(self, tx_id: int, category: str) -> None:
        self.conn.execute(
            "UPDATE transactions SET category = ? WHERE id = ?", (category, tx_id)
        )
        self.conn.commit()

    def top_payees(self, month: str, limit: int = 10) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """SELECT payee, COUNT(*) AS n, SUM(amount_minor) AS total
                   FROM transactions
                   WHERE substr(date, 1, 7) = ? AND amount_minor < 0
                   GROUP BY payee ORDER BY total ASC LIMIT ?""",
                (month, limit),
            ).fetchall()
        )

    # -- rules ------------------------------------------------------------
    def add_rule(self, pattern: str, category: str) -> int:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO rules(pattern, category) VALUES (?, ?)",
            (pattern.strip().lower(), category.strip()),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_rules(self) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM rules ORDER BY pattern").fetchall())

    def delete_rule(self, rule_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def match_rule(self, payee: str) -> str | None:
        """First rule whose pattern appears in the payee (longest match wins)."""
        needle = payee.lower()
        best: str | None = None
        best_len = -1
        for row in self.list_rules():
            if row["pattern"] in needle and len(row["pattern"]) > best_len:
                best = row["category"]
                best_len = len(row["pattern"])
        return best

    # -- budgets ----------------------------------------------------------
    def set_budget(self, category: str, month: str, limit_minor: int) -> None:
        self.conn.execute(
            """INSERT INTO budgets(category, month, limit_minor) VALUES (?, ?, ?)
               ON CONFLICT(category, month) DO UPDATE SET limit_minor = excluded.limit_minor""",
            (category.strip(), month, limit_minor),
        )
        self.conn.commit()

    def list_budgets(self, month: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM budgets WHERE month = ? ORDER BY category", (month,)
            ).fetchall()
        )

    # -- balances / net worth ---------------------------------------------
    def set_balance(self, account_id: int, date: str, balance_minor: int) -> None:
        self.conn.execute(
            """INSERT INTO balances(account_id, date, balance_minor) VALUES (?, ?, ?)
               ON CONFLICT(account_id, date) DO UPDATE SET balance_minor = excluded.balance_minor""",
            (account_id, date, balance_minor),
        )
        self.conn.commit()

    def net_worth(self, date: str | None = None) -> list[sqlite3.Row]:
        """Latest balance snapshot per account (optionally as of a date)."""
        if date:
            sql = """SELECT a.name, b.balance_minor, b.date FROM accounts a
                     JOIN balances b ON b.account_id = a.id
                     WHERE b.date = (SELECT MAX(date) FROM balances
                                     WHERE account_id = a.id AND date <= ?)"""
            return list(self.conn.execute(sql, (date,)).fetchall())
        sql = """SELECT a.name, b.balance_minor, b.date FROM accounts a
                 JOIN balances b ON b.account_id = a.id
                 WHERE b.date = (SELECT MAX(date) FROM balances WHERE account_id = a.id)"""
        return list(self.conn.execute(sql).fetchall())

    @staticmethod
    def _row_to_tx(row: sqlite3.Row) -> Transaction:
        return Transaction(
            id=row["id"],
            date=row["date"],
            amount_minor=row["amount_minor"],
            payee=row["payee"],
            category=row["category"],
            account_id=row["account_id"],
            note=row["note"],
            source=row["source"],
        )
