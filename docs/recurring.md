# Recurring charges — the subscription audit

```bash
pocketledger recurring
```

```
recurring charges — est. $15.49 / month in spending
acme salary                   $3,200.00  every ~30d  x4  2026-08-20 → 2026-11-03  ≈ $3,200.00/mo
netflix                         -$15.49  every ~30d  x5  2026-08-15 → 2026-11-04  ≈ $15.49/mo
```

## How detection works

1. Transactions are grouped by **normalised payee** (case, punctuation,
   digits and merchant suffixes stripped) and **exact amount**.
2. A group needs **3+ occurrences** with a roughly regular gap
   (median gap 5–40 days, largest gap no more than 3× the median).
3. Monthly cost is estimated from the cadence: monthly gaps → the
   amount itself, weekly gaps → amount × 4.

Income (like a salary) is detected too and shown with a positive amount;
the header total counts **spending only**.

## What it cannot do

- It cannot detect a subscription that changes price every month, or
  one charged under a different merchant name each time.
- A yearly subscription needs a year of data before it appears.
- It is a heuristic, not a bank feed: if a charge looks wrong, check
  your statement. See `docs/limits.md`.
