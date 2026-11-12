# Support

## Getting help

- **First stop:** `docs/faq.md` and `pocketledger doctor` — the doctor
  command tells you exactly what is uncategorized, duplicated, or
  future-dated in your ledger.
- **Bugs:** open an issue with the bug-report template and paste the
  command and the output (never paste your real ledger or real bank CSV
  — use `examples/bank-sample-a.csv` to reproduce instead).
- **Ideas:** open a feature request. Import-format requests are welcome —
  tell us the bank and paste the CSV header row (with amounts removed).

## Before you open an issue

1. Run `pocketledger --version` and include the version.
2. Run `pocketledger doctor` — it usually names the problem.
3. Try the failing import on `examples/bank-sample-a.csv` first, to
   separate a pocketledger bug from a quirk of your bank's file.

## No commercial support

pocketledger is a personal open-source project maintained in spare time.
There is no paid support tier and no SLA — but issues with a clear
reproduction get answered first.
