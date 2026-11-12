# Importing bank CSVs

## Supported layouts

pocketledger detects columns from the header row. It understands:

| Layout | Example headers |
|---|---|
| Single amount | `Date, Description, Amount` |
| Split debit/credit | `Transaction Date, Merchant, Debit, Credit` |
| No header | positional guess: date, payee, amount |

Header aliases include `Transaction Date`, `Posted Date`, `Value Date`,
`Merchant`, `Counterparty`, `Memo`, `Narrative`, `Withdrawal`, `Deposit`
— if your bank uses a different name, open an issue with the header row
(amounts removed) and it will be added.

## Dates

`YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, `DD.MM.YYYY` and `YYYY/MM/DD`
are all accepted. Ambiguous dates (both fields ≤ 12) are read as
**DD/MM/YYYY** — the common bank format outside the US. If your bank
exports MM/DD/YYYY with ambiguous dates, normalise the file first or
open an issue.

## Amounts

`1,234.56`, `-42.00`, `($12.34)`, `€9.99`, `12,50` (European decimal)
all parse correctly. All amounts are stored as integer cents — no floats,
no rounding drift.

## Dedupe

Every transaction gets a fingerprint of date + amount + payee + account.
Importing the same file twice adds nothing; the second run reports
`skipped duplicates: N`. A genuinely repeated charge on a different day
is a different transaction and is kept.

## What import does not do

- It never modifies your CSV.
- It never guesses a category it cannot match — unmatched rows stay
  `Uncategorized` for you to teach (see `categories.md`).
- It never sends anything anywhere. The file is read, parsed, and stored
  locally.
