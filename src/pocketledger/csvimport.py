"""Bank CSV import with automatic column detection and dedupe.

Banks all export different CSV layouts. pocketledger detects the date,
amount and payee columns by header names (with a small alias table), and
falls back to positional guessing when headers are missing. Every row is
deduped by fingerprint, so importing the same file twice adds nothing.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from .money import MoneyError, parse_amount
from .store import Store

_DATE_ALIASES = {
    "date", "transaction date", "posted date", "value date", "booking date",
    "trans date", "txn date", "date posted", "completed date",
}
_AMOUNT_ALIASES = {
    "amount", "amount (usd)", "amount (eur)", "amount (gbp)", "value",
    "transaction amount", "total", "sum", "debit/credit",
}
_PAYEE_ALIASES = {
    "payee", "description", "merchant", "name", "transaction", "details",
    "memo", "narrative", "counterparty", "recipient", "vendor",
}
_DEBIT_ALIASES = {"debit", "withdrawal", "money out", "out", "spent", "charge"}
_CREDIT_ALIASES = {"credit", "deposit", "money in", "in", "received", "income"}
_NOTE_ALIASES = {"note", "notes", "category", "reference", "ref", "type", "status"}

_DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),          # 2026-11-10
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),          # 11/10/2026 or 10/11/2026
    re.compile(r"^\d{2}-\d{2}-\d{4}$"),          # 10-11-2026
    re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),        # 10.11.2026
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),          # 2026/11/10
)


@dataclass
class ImportResult:
    imported: int = 0
    skipped_duplicates: int = 0
    skipped_bad_rows: int = 0
    categorised: int = 0
    errors: list[str] = field(default_factory=list)


def normalise_date(raw: str) -> str:
    """Normalise a bank date string to ISO ``YYYY-MM-DD``.

    Ambiguous ``DD/MM/YYYY`` vs ``MM/DD/YYYY``: if the first field is > 12
    it must be the day; otherwise assume DD/MM (the common bank format
    outside the US) and document it. Unparseable input raises ValueError.
    """
    text = raw.strip()
    for pattern in _DATE_PATTERNS:
        if not pattern.match(text):
            continue
        if "-" in text and len(text.split("-")[0]) == 4:  # YYYY-MM-DD
            return text
        if "/" in text and len(text.split("/")[0]) == 4:  # YYYY/MM/DD
            y, m, d = text.split("/")
            return f"{y}-{m}-{d}"
        sep = "/" if "/" in text else ("-" if "-" in text else ".")
        a, b, c = text.split(sep)
        first, second = int(a), int(b)
        if first > 12:  # definitely DD/MM/YYYY
            day, month = first, second
        elif second > 12:  # definitely MM/DD/YYYY
            month, day = first, second
        else:  # ambiguous: assume DD/MM/YYYY (documented in docs/importing.md)
            day, month = first, second
        return f"{c}-{month:02d}-{day:02d}"
    raise ValueError(f"unrecognised date: {raw!r}")


def detect_columns(header: list[str]) -> dict[str, int]:
    """Map logical column names to CSV column indexes from a header row."""
    lowered = [h.strip().lower() for h in header]
    found: dict[str, int] = {}
    for idx, name in enumerate(lowered):
        if name in _DATE_ALIASES and "date" not in found:
            found["date"] = idx
        elif name in _AMOUNT_ALIASES and "amount" not in found:
            found["amount"] = idx
        elif name in _PAYEE_ALIASES and "payee" not in found:
            found["payee"] = idx
        elif name in _DEBIT_ALIASES and "debit" not in found:
            found["debit"] = idx
        elif name in _CREDIT_ALIASES and "credit" not in found:
            found["credit"] = idx
        elif name in _NOTE_ALIASES and "note" not in found:
            found["note"] = idx
    return found


def import_csv(
    store: Store,
    text: str,
    account_id: int | None = None,
    *,
    date_format_hint: str | None = None,
) -> ImportResult:
    """Import CSV text into the store. Returns counts and row-level errors."""
    result = ImportResult()
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        result.errors.append("empty file")
        return result

    columns = detect_columns(rows[0])
    data_rows = rows[1:] if columns else rows
    if not columns:
        # No header at all: guess date, payee, amount by position (0, 1, 2).
        columns = {"date": 0, "payee": 1, "amount": 2}

    for lineno, row in enumerate(data_rows, start=2 if columns else 1):
        try:
            date_raw = row[columns["date"]].strip()
            date = normalise_date(date_raw)
            payee = row[columns["payee"]].strip() if "payee" in columns else ""
            note = row[columns["note"]].strip() if "note" in columns else ""

            if "amount" in columns:
                amount_minor, _currency = parse_amount(row[columns["amount"]])
            elif "debit" in columns or "credit" in columns:
                debit = row[columns["debit"]].strip() if "debit" in columns else ""
                credit = row[columns["credit"]].strip() if "credit" in columns else ""
                if debit:
                    amount_minor, _ = parse_amount(debit)
                    amount_minor = -abs(amount_minor)
                elif credit:
                    amount_minor, _ = parse_amount(credit)
                    amount_minor = abs(amount_minor)
                else:
                    raise MoneyError("both debit and credit empty")
            else:
                raise MoneyError("no amount column found")

            category = store.match_rule(payee) or "Uncategorized"
            _row_id, inserted = store.add_transaction(
                date=date,
                amount_minor=amount_minor,
                payee=payee,
                category=category,
                account_id=account_id,
                note=note,
                source="import",
            )
            if inserted:
                result.imported += 1
                if category != "Uncategorized":
                    result.categorised += 1
            else:
                result.skipped_duplicates += 1
        except (ValueError, MoneyError, IndexError) as exc:
            result.skipped_bad_rows += 1
            if len(result.errors) < 10:
                result.errors.append(f"row {lineno}: {exc}")
    return result
