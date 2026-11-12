# Limits — what v0.1.0 honestly does not do

- **CSV only.** No OFX/QIF import, no bank API, no live sync. You export
  the file; pocketledger reads it.
- **One currency per ledger.** Amounts in a second currency are stored
  as-is with no conversion. Multi-currency is planned.
- **Ambiguous dates assume DD/MM/YYYY.** See `docs/importing.md`. A bank
  that exports MM/DD/YYYY with ambiguous dates will be misread — check
  the first import carefully.
- **Recurring detection is heuristic.** Price changes, renamed merchants
  and yearly charges can be missed. It is a starting point for your
  subscription audit, not a guarantee.
- **Rules are substring matches, not ML.** A rule like `apple` matches
  both Apple the company and Apple the grocery item. Use longer patterns
  (`apple.com/bill`) for precision.
- **No mobile app, no sync.** One SQLite file on one machine. Back it up
  yourself.
- **Not tax or investment software.** Reports show income, spending and
  savings rate; they are not tax advice and pocketledger tracks no
  investments.
- **Single user.** No multi-user ledgers, no permissions model — the file
  is yours alone.
