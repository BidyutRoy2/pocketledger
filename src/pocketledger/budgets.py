"""Monthly budgets: set a spending cap per category, check where you stand.

Budgets are spending caps (money out) per category per month. A report
shows spent vs limit, remaining, and a status band (OK / Watch / Over).
Unbudgeted categories are simply not shown — no nagging by default.
"""

from __future__ import annotations

from dataclasses import dataclass

from .store import Store


@dataclass
class BudgetStatus:
    category: str
    month: str
    limit_minor: int
    spent_minor: int

    @property
    def remaining_minor(self) -> int:
        return self.limit_minor - self.spent_minor

    @property
    def pct_used(self) -> float:
        if self.limit_minor <= 0:
            return 0.0
        return self.spent_minor / self.limit_minor * 100

    @property
    def status(self) -> str:
        if self.spent_minor > self.limit_minor:
            return "OVER"
        if self.pct_used >= 80:
            return "WATCH"
        return "OK"


def budget_statuses(store: Store, month: str) -> list[BudgetStatus]:
    """Budget status for every budget set in ``month``."""
    spent = {
        row["category"]: -row["total"]
        for row in store.sum_by_category(month)
        if row["total"] is not None and row["total"] < 0
    }
    out: list[BudgetStatus] = []
    for row in store.list_budgets(month):
        out.append(
            BudgetStatus(
                category=row["category"],
                month=month,
                limit_minor=row["limit_minor"],
                spent_minor=spent.get(row["category"], 0),
            )
        )
    return sorted(out, key=lambda b: b.pct_used, reverse=True)
