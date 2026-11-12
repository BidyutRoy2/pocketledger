"""Command-line interface for pocketledger.

Every command works on a ledger directory containing ``ledger.db``.
Run ``pocketledger init`` once, then import a bank CSV and get a report.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .budgets import budget_statuses
from .categorize import categorise_all, install_starter_rules, learn_from
from .csvimport import import_csv, normalise_date
from .money import MoneyError, format_amount, parse_amount
from .recurring import detect_recurring
from .report import build_report, render_html, render_markdown
from .store import Store

DEFAULT_LEDGER_DIR = Path.home() / "pocketledger"


def _resolve_ledger_dir(args) -> Path:
    return Path(args.ledger) if args.ledger else DEFAULT_LEDGER_DIR


def _open(args) -> tuple[Store, Path]:
    ledger_dir = _resolve_ledger_dir(args)
    db = ledger_dir / "ledger.db"
    if not db.exists():
        print(f"no ledger at {ledger_dir} — run `pocketledger init` first", file=sys.stderr)
        raise SystemExit(2)
    return Store(db), ledger_dir


def _valid_month(value: str) -> str:
    try:
        year, month = value.split("-")
        if len(year) != 4 or not (1 <= int(month) <= 12):
            raise ValueError
        return f"{int(year):04d}-{int(month):02d}"
    except ValueError:
        raise argparse.ArgumentTypeError(f"month must be YYYY-MM, got {value!r}")


def _valid_date(value: str) -> str:
    try:
        return normalise_date(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))


# ---------------------------------------------------------------- commands
def cmd_init(args) -> int:
    ledger_dir = _resolve_ledger_dir(args)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    db = ledger_dir / "ledger.db"
    fresh = not db.exists()
    store = Store(db)
    if args.account:
        if store.get_account(args.account) is None:
            store.add_account(args.account, kind=args.kind, currency=args.currency)
            print(f"account created: {args.account} ({args.kind}, {args.currency})")
    if args.starter_rules:
        added = install_starter_rules(store)
        print(f"starter rules installed: {added} rules")
    store.close()
    print(f"ledger ready at {ledger_dir}")
    if fresh:
        print("next: pocketledger import bank.csv --account <name>")
    return 0


def cmd_account(args) -> int:
    store, _ = _open(args)
    if args.action == "add":
        try:
            store.add_account(args.name, kind=args.kind, currency=args.currency)
        except Exception as exc:  # duplicate name
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"account added: {args.name} ({args.kind}, {args.currency})")
    else:
        rows = store.list_accounts()
        if not rows:
            print("no accounts yet — run `pocketledger account add <name>`")
        for row in rows:
            print(f"{row['name']:<24} {row['kind']:<12} {row['currency']}")
    store.close()
    return 0


def cmd_add(args) -> int:
    store, _ = _open(args)
    account_id = None
    if args.account:
        account = store.get_account(args.account)
        if account is None:
            print(f"unknown account: {args.account}", file=sys.stderr)
            return 1
        account_id = account["id"]
    try:
        amount_minor, _ = parse_amount(args.amount)
    except MoneyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.direction == "out":
        amount_minor = -abs(amount_minor)
    else:
        amount_minor = abs(amount_minor)
    category = args.category
    if not category:
        category = store.match_rule(args.payee) or "Uncategorized"
    _row_id, inserted = store.add_transaction(
        date=args.date,
        amount_minor=amount_minor,
        payee=args.payee,
        category=category,
        account_id=account_id,
        note=args.note or "",
    )
    if not inserted:
        print("duplicate transaction — already in the ledger")
        return 1
    print(f"added: {args.date} {format_amount(amount_minor)} {args.payee} [{category}]")
    store.close()
    return 0


def cmd_import(args) -> int:
    store, _ = _open(args)
    account_id = None
    if args.account:
        account = store.get_account(args.account)
        if account is None:
            print(f"unknown account: {args.account}", file=sys.stderr)
            return 1
        account_id = account["id"]
    text = Path(args.file).read_text(encoding="utf-8-sig")
    result = import_csv(store, text, account_id)
    print(f"imported: {result.imported}")
    print(f"skipped duplicates: {result.skipped_duplicates}")
    if result.categorised:
        print(f"auto-categorised: {result.categorised} transactions")
    if result.skipped_bad_rows:
        print(f"skipped bad rows: {result.skipped_bad_rows}")
    for err in result.errors:
        print(f"  {err}")
    store.close()
    return 0


def cmd_list(args) -> int:
    store, _ = _open(args)
    account_id = None
    if args.account:
        account = store.get_account(args.account)
        if account is None:
            print(f"unknown account: {args.account}", file=sys.stderr)
            return 1
        account_id = account["id"]
    txs = store.list_transactions(
        month=args.month, category=args.category, account_id=account_id, limit=args.limit
    )
    if not txs:
        print("no transactions match")
        return 0
    total = 0
    for tx in txs:
        total += tx.amount_minor
        print(f"{tx.date} {format_amount(tx.amount_minor):>12}  {tx.payee[:36]:<36} [{tx.category}]")
    print(f"{'-' * 60}\n{len(txs)} transactions, net {format_amount(total)}")
    store.close()
    return 0


def cmd_categorize(args) -> int:
    store, _ = _open(args)
    if args.learn:
        payee, category = args.learn
        try:
            learn_from(store, payee, category)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"learned rule: {payee!r} -> {category}")
        changed = categorise_all(store)
        print(f"applied to {changed} existing transactions")
        return 0
    changed = categorise_all(store)
    remaining = len(store.uncategorized())
    print(f"categorised: {changed} transactions")
    print(f"still uncategorized: {remaining}")
    if remaining and args.show:
        for tx in store.uncategorized()[:20]:
            print(f"  {tx.date} {format_amount(tx.amount_minor):>12}  {tx.payee}")
    store.close()
    return 0


def cmd_rule(args) -> int:
    store, _ = _open(args)
    if args.action == "add":
        store.add_rule(args.pattern, args.category)
        print(f"rule added: {args.pattern!r} -> {args.category}")
    elif args.action == "delete":
        rule_id = args.rule_id
        if rule_id is None and args.pattern is not None:
            try:
                rule_id = int(args.pattern)
            except ValueError:
                rule_id = None
        if rule_id is None:
            print("usage: pocketledger rule delete <id>", file=sys.stderr)
            return 1
        if store.delete_rule(rule_id):
            print(f"rule {rule_id} deleted")
        else:
            print(f"no rule with id {rule_id}", file=sys.stderr)
            return 1
    else:
        rules = store.list_rules()
        if not rules:
            print("no rules yet — run `pocketledger rule add <pattern> <category>`")
        for row in rules:
            print(f"{row['id']:>4}  {row['pattern']:<28} -> {row['category']}")
    store.close()
    return 0


def cmd_budget(args) -> int:
    store, _ = _open(args)
    month = args.month or date.today().strftime("%Y-%m")
    if args.set is not None:
        category, amount = args.set
        try:
            limit_minor, _ = parse_amount(amount)
        except MoneyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        store.set_budget(category, month, abs(limit_minor))
        print(f"budget set: {category} {format_amount(abs(limit_minor))} / month ({month})")
        return 0
    statuses = budget_statuses(store, month)
    if not statuses:
        print(f"no budgets for {month} — run `pocketledger budget --set <category> <amount>`")
        return 0
    print(f"budgets for {month}")
    for b in statuses:
        bar = "█" * int(min(b.pct_used, 100) / 5) + "░" * (20 - int(min(b.pct_used, 100) / 5))
        print(f"{b.category:<16} {format_amount(b.spent_minor):>10} / {format_amount(b.limit_minor):>10} "
              f"{bar} {b.pct_used:5.0f}% {b.status}")
    store.close()
    return 0


def cmd_report(args) -> int:
    store, _ = _open(args)
    month = args.month or date.today().strftime("%Y-%m")
    report = build_report(store, month)
    if args.format == "json":
        cats = [
            {"category": r["category"], "count": r["n"], "total_minor": r["total"]}
            for r in store.sum_by_category(month)
        ]
        print(json.dumps({
            "month": month,
            "income_minor": report.income_minor,
            "spending_minor": report.spending_minor,
            "savings_minor": report.savings_minor,
            "savings_rate_pct": round(report.savings_rate, 1),
            "categories": cats,
        }, indent=2))
        return 0
    if args.format == "html":
        out = Path(args.output) if args.output else Path(f"pocketledger-{month}.html")
        out.write_text(render_html(store, report), encoding="utf-8")
        print(f"report written to {out}")
        return 0
    print(render_markdown(store, report))
    if args.output:
        Path(args.output).write_text(render_markdown(store, report), encoding="utf-8")
        print(f"report written to {args.output}")
    store.close()
    return 0


def cmd_recurring(args) -> int:
    store, _ = _open(args)
    found = detect_recurring(store)
    if not found:
        print("no recurring charges found (need 3+ similar transactions)")
        return 0
    spending_monthly = sum(r.monthly_cost_minor for r in found if r.amount_minor < 0)
    print(f"recurring charges — est. {format_amount(spending_monthly)} / month in spending")
    for r in found:
        print(f"{r.payee:<28} {format_amount(r.amount_minor):>10}  "
              f"every ~{r.median_gap_days}d  x{r.occurrences}  "
              f"{r.first_date} → {r.last_date}"
              + (f"  ≈ {format_amount(r.monthly_cost_minor)}/mo" if r.monthly_cost_minor else ""))
    store.close()
    return 0


def cmd_balance(args) -> int:
    store, _ = _open(args)
    account = store.get_account(args.account)
    if account is None:
        print(f"unknown account: {args.account}", file=sys.stderr)
        return 1
    try:
        balance_minor, _ = parse_amount(args.amount)
    except MoneyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    store.set_balance(account["id"], args.date, balance_minor)
    print(f"balance recorded: {args.account} {format_amount(balance_minor)} on {args.date}")
    store.close()
    return 0


def cmd_networth(args) -> int:
    store, _ = _open(args)
    rows = store.net_worth(args.date)
    if not rows:
        print("no balance snapshots yet — run `pocketledger balance <account> <amount>`")
        return 0
    total = sum(r["balance_minor"] for r in rows)
    for r in rows:
        print(f"{r['name']:<24} {format_amount(r['balance_minor']):>12}  (as of {r['date']})")
    print(f"{'-' * 48}\nnet worth: {format_amount(total)}")
    store.close()
    return 0


def cmd_export(args) -> int:
    store, _ = _open(args)
    txs = store.list_transactions(month=args.month, limit=100_000)
    if args.format == "json":
        data = [{
            "date": t.date, "amount_minor": t.amount_minor, "payee": t.payee,
            "category": t.category, "note": t.note, "source": t.source,
        } for t in txs]
        out = json.dumps(data, indent=2)
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["date", "amount_minor", "payee", "category", "note", "source"])
        for t in txs:
            writer.writerow([t.date, t.amount_minor, t.payee, t.category, t.note, t.source])
        out = buf.getvalue()
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"exported {len(txs)} transactions to {args.output}")
    else:
        print(out, end="")
    store.close()
    return 0


def cmd_doctor(args) -> int:
    store, _ = _open(args)
    problems = 0
    n = store.count_transactions()
    print(f"transactions: {n}")
    unc = store.uncategorized()
    print(f"uncategorized: {len(unc)}")
    if unc:
        problems += 1
        print("  run `pocketledger categorize` or `pocketledger categorize --learn <payee> <category>`")
    # Duplicate fingerprints cannot exist (UNIQUE), but same payee+amount on
    # the same day from different accounts is worth flagging.
    dupes = store.conn.execute(
        """SELECT date, amount_minor, payee, COUNT(*) AS c FROM transactions
           GROUP BY date, amount_minor, payee HAVING c > 1"""
    ).fetchall()
    print(f"possible duplicate groups: {len(dupes)}")
    if dupes:
        problems += 1
        for row in dupes[:5]:
            print(f"  {row['date']} {format_amount(row['amount_minor'])} {row['payee']} x{row['c']}")
    future = store.conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE date > date('now')"
    ).fetchone()[0]
    print(f"future-dated transactions: {future}")
    if future:
        problems += 1
    accounts = store.list_accounts()
    print(f"accounts: {len(accounts)}")
    if not accounts:
        problems += 1
        print("  no accounts — run `pocketledger account add <name>`")
    print("OK" if problems == 0 else f"{problems} issue(s) found")
    store.close()
    return 0 if problems == 0 else 1


# ---------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pocketledger",
        description="Local-first personal finance ledger. Your money stays on your disk.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--ledger", default=None,
                        help="ledger directory (default: ~/pocketledger)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a ledger")
    p.add_argument("--account", help="create a first account")
    p.add_argument("--kind", default="checking", help="account kind (default: checking)")
    p.add_argument("--currency", default="USD", help="account currency (default: USD)")
    p.add_argument("--starter-rules", action="store_true",
                   help="install the starter categorisation rules")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("account", help="manage accounts")
    p.add_argument("action", choices=["add", "list"], nargs="?", default="list")
    p.add_argument("name", nargs="?", help="account name (for add)")
    p.add_argument("--kind", default="checking")
    p.add_argument("--currency", default="USD")
    p.set_defaults(func=cmd_account)

    p = sub.add_parser("add", help="add one transaction")
    p.add_argument("--date", type=_valid_date, default=date.today().isoformat())
    p.add_argument("--amount", required=True, help="e.g. 12.50 (use --direction out for spending)")
    p.add_argument("--direction", choices=["in", "out"], default="out")
    p.add_argument("--payee", required=True)
    p.add_argument("--category", help="defaults to rule match or Uncategorized")
    p.add_argument("--account", help="account name")
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("import", help="import a bank CSV")
    p.add_argument("file", help="path to the CSV file")
    p.add_argument("--account", help="account name to attach transactions to")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("list", help="list transactions")
    p.add_argument("--month", type=_valid_month)
    p.add_argument("--category")
    p.add_argument("--account")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("categorize", help="apply rules to uncategorized transactions")
    p.add_argument("--learn", nargs=2, metavar=("PAYEE", "CATEGORY"),
                   help="learn a payee -> category rule and apply it")
    p.add_argument("--show", action="store_true", help="show remaining uncategorized rows")
    p.set_defaults(func=cmd_categorize)

    p = sub.add_parser("rule", help="manage categorisation rules")
    p.add_argument("action", choices=["add", "list", "delete"], nargs="?", default="list")
    p.add_argument("pattern", nargs="?", help="payee substring to match (for add)")
    p.add_argument("category", nargs="?", help="category to assign (for add)")
    p.add_argument("rule_id", nargs="?", type=int, help="rule id (for delete)")
    p.set_defaults(func=cmd_rule)

    p = sub.add_parser("budget", help="monthly spending budgets")
    p.add_argument("--month", type=_valid_month, help="YYYY-MM (default: this month)")
    p.add_argument("--set", nargs=2, metavar=("CATEGORY", "AMOUNT"),
                   help="set a monthly budget, e.g. --set Groceries 400")
    p.set_defaults(func=cmd_budget)

    p = sub.add_parser("report", help="monthly report")
    p.add_argument("--month", type=_valid_month, help="YYYY-MM (default: this month)")
    p.add_argument("--format", choices=["markdown", "html", "json"], default="markdown")
    p.add_argument("--output", help="write the report to a file")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("recurring", help="find recurring charges / subscriptions")
    p.set_defaults(func=cmd_recurring)

    p = sub.add_parser("balance", help="record an account balance snapshot")
    p.add_argument("account", help="account name")
    p.add_argument("amount", help="balance, e.g. 1250.00")
    p.add_argument("--date", type=_valid_date, default=date.today().isoformat())
    p.set_defaults(func=cmd_balance)

    p = sub.add_parser("networth", help="show net worth from balance snapshots")
    p.add_argument("--date", type=_valid_date, help="as of date (default: latest)")
    p.set_defaults(func=cmd_networth)

    p = sub.add_parser("export", help="export transactions as CSV or JSON")
    p.add_argument("--month", type=_valid_month)
    p.add_argument("--format", choices=["csv", "json"], default="csv")
    p.add_argument("--output", help="write to a file instead of stdout")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("doctor", help="check ledger health")
    p.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Force UTF-8 output: Windows consoles default to cp1252, which cannot
    # print the characters this CLI uses (budget bar █/░, report em dash —,
    # recurring →/≈). Without this the CLI crashes on Windows with
    # UnicodeEncodeError and the CI Tests step fails there only.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
