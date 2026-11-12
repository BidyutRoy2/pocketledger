# pocketledger v0.1.0 — Release Notes

**Your money, your disk, your rules.** A local-first personal finance
ledger: import bank CSVs, auto-categorise, set budgets, audit your
subscriptions, and track net worth — with zero dependencies, zero
accounts, and zero data leaving your machine.

## What you get

- **Bank CSV import that just works** — automatic column detection, split
  Debit/Credit files, DD/MM and MM/DD dates, and dedupe so re-importing
  the same file adds nothing.
- **Auto-categorisation that learns** — 27 starter rules, plus
  `categorize --learn` teaches the ledger from your corrections.
- **Budgets with honest status** — OK / WATCH / OVER, no nagging for
  categories you never budgeted.
- **Subscription audit** — `pocketledger recurring` finds the charges
  that quietly repeat every month and totals them.
- **Reports you can open anywhere** — Markdown, JSON, or a self-contained
  dark-mode HTML dashboard.
- **Net worth tracking** — balance snapshots per account, no bank login
  required.

## Install (source — the package is not on PyPI yet)

```bash
git clone https://github.com/BidyutRoy2/pocketledger.git
cd pocketledger
python3 -m pip install -e .
pocketledger init --account Main --starter-rules
```

## Try it in 60 seconds

```bash
bash examples/demo.sh
```

## What's next

- OFX/QIF import, multi-currency ledgers, and a yearly trends report.
- See `docs/limits.md` for what v0.1.0 deliberately does not do.
