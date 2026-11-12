# Changelog

All notable changes to pocketledger are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-11

### Added

- `pocketledger init` — create a local ledger (SQLite, `ledger.db`) with an
  optional first account and 27 starter categorisation rules.
- `pocketledger import` — import bank CSVs with automatic column detection
  (single Amount column or split Debit/Credit), DD/MM/YYYY and MM/DD/YYYY
  dates, and fingerprint dedupe — re-importing the same file adds nothing.
- `pocketledger add` / `list` — add one transaction, list with month /
  category / account filters.
- `pocketledger categorize` / `rule` — rule-based auto-categorisation
  (longest-match wins) and `categorize --learn <payee> <category>` to teach
  the ledger from a correction.
- `pocketledger budget` — monthly spending caps per category with OK /
  WATCH (≥80%) / OVER status bands.
- `pocketledger report` — monthly Markdown, JSON, or self-contained
  dark-mode HTML report: income, spending, savings rate, spending by
  category, top payees, budget status.
- `pocketledger recurring` — subscription audit: detects recurring charges
  (≥3 similar transactions, regular cadence) with an estimated monthly cost.
- `pocketledger balance` / `networth` — balance snapshots per account and
  net worth from the latest snapshot.
- `pocketledger export` — CSV / JSON export of the whole ledger.
- `pocketledger doctor` — ledger health: uncategorized rows, possible
  duplicate groups, future-dated transactions, missing accounts.
- Exact money math: all amounts stored as integer minor units (cents);
  no floats anywhere in money paths.
- 77 unit and end-to-end tests (unittest, zero dependencies).
