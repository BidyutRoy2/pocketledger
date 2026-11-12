"""Recurring-charge detection (subscriptions and regular bills).

A recurring charge is a group of transactions with the same normalised
payee and (nearly) the same amount, appearing at least 3 times, with a
roughly regular gap between occurrences. This is how pocketledger finds
the subscriptions you forgot about — the "subscription audit" is the
single most useful report for most people.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .store import Store, Transaction

# Payees are normalised before grouping: case, punctuation, digits and
# common merchant suffixes are stripped so "NETFLIX.COM" and
# "Netflix 1234" group together.
_SUFFIXES = ("com", "inc", "ltd", "llc", "co", "corp", "store", "online")


def normalise_payee(payee: str) -> str:
    text = payee.lower()
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^a-z ]+", " ", text)
    words = [w for w in text.split() if w not in _SUFFIXES]
    return " ".join(words).strip()


@dataclass
class RecurringCharge:
    payee: str
    amount_minor: int  # typical (median) amount, negative = money out
    occurrences: int
    first_date: str
    last_date: str
    median_gap_days: int
    monthly_cost_minor: int  # estimated cost per month (0 if not monthly-ish)


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def detect_recurring(store: Store, *, min_occurrences: int = 3) -> list[RecurringCharge]:
    """Detect recurring charges across the whole ledger."""
    all_tx = store.list_transactions(limit=100_000)
    groups: dict[tuple[str, int], list[Transaction]] = {}
    for tx in all_tx:
        key = (normalise_payee(tx.payee), tx.amount_minor)
        groups.setdefault(key, []).append(tx)

    found: list[RecurringCharge] = []
    for (payee, amount), txs in groups.items():
        if len(txs) < min_occurrences or not payee:
            continue
        dates = sorted(date.fromisoformat(t.date) for t in txs)
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        # Cadence is the median gap, ignoring sub-10-day gaps: a second
        # charge a few days after the first (e.g. the same subscription
        # appearing in two bank files) is not the billing cadence.
        cadence_gaps = [g for g in gaps if g >= 10] or gaps
        median_gap = _median(cadence_gaps)
        # Regular cadence: median gap between 5 and 40 days, and the
        # largest gap no more than 3x the median (allows one missed month).
        if not (5 <= median_gap <= 40):
            continue
        if max(gaps) > 3 * median_gap + 7:
            continue
        monthly = 0
        if 25 <= median_gap <= 35:
            monthly = abs(amount)
        elif 6 <= median_gap <= 8:  # weekly
            monthly = abs(amount) * 4
        found.append(
            RecurringCharge(
                payee=payee,
                amount_minor=amount,
                occurrences=len(txs),
                first_date=dates[0].isoformat(),
                last_date=dates[-1].isoformat(),
                median_gap_days=median_gap,
                monthly_cost_minor=monthly,
            )
        )
    return sorted(found, key=lambda r: r.monthly_cost_minor, reverse=True)
