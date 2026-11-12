"""Monthly reports: Markdown and a self-contained dark-mode HTML dashboard.

Everything is computed from the ledger file with plain SQL — no network,
no templates engine, no dependencies. The HTML report embeds its own CSS
and works offline by opening the file in a browser.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from .budgets import budget_statuses
from .money import format_amount
from .store import Store

_CSS = """
:root { color-scheme: dark; --bg: #0d1117; --panel: #161b22; --line: #30363d;
        --text: #e6edf3; --muted: #8b949e; --green: #3fb950; --red: #f85149;
        --amber: #d29922; --accent: #58a6ff; }
body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif;
       margin: 0; padding: 32px; }
.wrap { max-width: 880px; margin: 0 auto; }
h1 { font-size: 28px; margin: 0 0 4px; }
.sub { color: var(--muted); margin: 0 0 24px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
.card .label { color: var(--muted); font-size: 13px; }
.card .value { font-size: 26px; font-weight: 700; margin-top: 4px; }
.pos { color: var(--green); } .neg { color: var(--red); }
h2 { font-size: 18px; margin: 28px 0 10px; }
table { width: 100%; border-collapse: collapse; background: var(--panel);
        border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .04em; }
tr:last-child td { border-bottom: none; }
.bar { height: 8px; background: #21262d; border-radius: 4px; overflow: hidden; min-width: 120px; }
.bar > div { height: 100%; background: var(--accent); }
.badge { padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.ok { background: rgba(63,185,80,.15); color: var(--green); }
.watch { background: rgba(210,153,34,.15); color: var(--amber); }
.over { background: rgba(248,81,73,.15); color: var(--red); }
.foot { color: var(--muted); font-size: 13px; margin-top: 28px; }
"""


@dataclass
class MonthReport:
    month: str
    income_minor: int
    spending_minor: int
    currency: str = "USD"

    @property
    def savings_minor(self) -> int:
        return self.income_minor - self.spending_minor

    @property
    def savings_rate(self) -> float:
        if self.income_minor <= 0:
            return 0.0
        return self.savings_minor / self.income_minor * 100


def build_report(store: Store, month: str) -> MonthReport:
    income, spending = store.month_totals(month)
    return MonthReport(month=month, income_minor=income, spending_minor=spending)


def render_markdown(store: Store, report: MonthReport) -> str:
    lines = [
        f"# pocketledger — {report.month}",
        "",
        f"- **Income:** {format_amount(report.income_minor)}",
        f"- **Spending:** {format_amount(report.spending_minor)}",
        f"- **Saved:** {format_amount(report.savings_minor)} "
        f"({report.savings_rate:.1f}% savings rate)",
        "",
        "## Spending by category",
        "",
        "| Category | Transactions | Total |",
        "|---|---:|---:|",
    ]
    for row in store.sum_by_category(report.month):
        if row["total"] is None or row["total"] >= 0:
            continue
        lines.append(
            f"| {row['category']} | {row['n']} | {format_amount(-row['total'])} |"
        )
    lines += ["", "## Top payees", "", "| Payee | Transactions | Total |",
              "|---|---:|---:|"]
    for row in store.top_payees(report.month):
        lines.append(
            f"| {html.escape(row['payee'])} | {row['n']} | {format_amount(-row['total'])} |"
        )
    budgets = budget_statuses(store, report.month)
    if budgets:
        lines += ["", "## Budgets", "", "| Category | Spent | Limit | Remaining | Status |",
                  "|---|---:|---:|---:|---|"]
        for b in budgets:
            lines.append(
                f"| {b.category} | {format_amount(b.spent_minor)} | "
                f"{format_amount(b.limit_minor)} | {format_amount(b.remaining_minor)} | "
                f"{b.status} ({b.pct_used:.0f}%) |"
            )
    lines.append("")
    lines.append("_Generated locally by pocketledger. Your data never left this machine._")
    return "\n".join(lines) + "\n"


def render_html(store: Store, report: MonthReport) -> str:
    cats = [r for r in store.sum_by_category(report.month)
            if r["total"] is not None and r["total"] < 0]
    max_spend = max((-r["total"] for r in cats), default=1)
    cat_rows = "".join(
        f"<tr><td>{html.escape(r['category'])}</td><td>{r['n']}</td>"
        f"<td><div class='bar'><div style='width:{-r['total'] / max_spend * 100:.0f}%'></div></div></td>"
        f"<td>{format_amount(-r['total'])}</td></tr>"
        for r in cats
    )
    payee_rows = "".join(
        f"<tr><td>{html.escape(r['payee'])}</td><td>{r['n']}</td>"
        f"<td>{format_amount(-r['total'])}</td></tr>"
        for r in store.top_payees(report.month)
    )
    budgets = budget_statuses(store, report.month)
    budget_section = ""
    if budgets:
        rows = "".join(
            f"<tr><td>{html.escape(b.category)}</td><td>{format_amount(b.spent_minor)}</td>"
            f"<td>{format_amount(b.limit_minor)}</td><td>{format_amount(b.remaining_minor)}</td>"
            f"<td><span class='badge {b.status.lower()}'>{b.status} {b.pct_used:.0f}%</span></td></tr>"
            for b in budgets
        )
        budget_section = (
            f"<h2>Budgets</h2><table><tr><th>Category</th><th>Spent</th>"
            f"<th>Limit</th><th>Remaining</th><th>Status</th></tr>{rows}</table>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>pocketledger — {report.month}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_CSS}</style></head>
<body><div class="wrap">
<h1>pocketledger — {report.month}</h1>
<p class="sub">Local-first monthly report. Generated on this machine; nothing was uploaded.</p>
<div class="cards">
<div class="card"><div class="label">Income</div><div class="value pos">{format_amount(report.income_minor)}</div></div>
<div class="card"><div class="label">Spending</div><div class="value neg">{format_amount(report.spending_minor)}</div></div>
<div class="card"><div class="label">Saved ({report.savings_rate:.0f}%)</div><div class="value">{format_amount(report.savings_minor)}</div></div>
</div>
<h2>Spending by category</h2>
<table><tr><th>Category</th><th>Txns</th><th></th><th>Total</th></tr>{cat_rows}</table>
<h2>Top payees</h2>
<table><tr><th>Payee</th><th>Txns</th><th>Total</th></tr>{payee_rows}</table>
{budget_section}
<p class="foot">Generated locally by pocketledger v0.1.0 — your data never left this machine.</p>
</div></body></html>
"""
