# FAQ

## Do I need an account or a subscription?

No. pocketledger is free, open source (MIT), and local-first. There is
no account to create and no server to pay for.

## Does it connect to my bank?

No. You export a CSV from your bank and import it. pocketledger never
sees your bank login.

## Where is my data?

In `~/pocketledger/ledger.db` (or the directory you pass with
`--ledger`). One SQLite file. Copy it to back up; delete it to start over.

## My bank's CSV did not import. What now?

Run `pocketledger import file.csv` and read the `skipped bad rows`
lines — they name the row and the reason. Common causes: a header name
pocketledger does not recognise (see `docs/importing.md`), or a date
format it cannot parse. Open an issue with the header row (amounts
removed) and it will be added.

## Why is a transaction Uncategorized?

No rule matched its payee. Teach it once and it will match forever:

```bash
pocketledger categorize --learn "Corner Bakery" Dining
```

## Can it do multiple currencies?

One currency per ledger today (set at account creation). Multi-currency
is on the roadmap; see `docs/limits.md`.

## Does it give financial advice?

No. pocketledger reports what you spent. It never tells you what to buy,
sell, or invest in.

## How is this different from a budgeting app?

Those apps hold your data on their servers and charge monthly. This one
holds your data on your disk and charges nothing. The trade-off: you
export CSVs yourself, and there is no mobile app (yet).
