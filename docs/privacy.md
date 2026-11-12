# Privacy

pocketledger is built on one rule: **your money stays on your disk.**

- **No network calls.** The code contains no HTTP client, no telemetry,
  no update check, no analytics. You can verify with `grep -r "http"
  src/` — the only URLs in the codebase are in documentation.
- **No account, no cloud, no sync.** Your ledger is a SQLite file
  (`~/pocketledger/ledger.db`). There is no server side to breach.
- **No bank login.** pocketledger reads CSV files you export yourself.
  It never asks for bank credentials and could not use them if you gave
  them.
- **Exports are yours.** `pocketledger export` writes CSV/JSON to a file
  you choose. Nothing is uploaded.

## Your responsibilities

- **Back up `ledger.db`.** It is the only copy of your finances. Copy
  it to encrypted storage; do not email it to yourself unencrypted.
- **Do not paste real data into issues.** Reproduce bugs with
  `examples/bank-sample-a.csv` or with amounts and payees changed.
- **Disk encryption matters.** Anyone who can read `ledger.db` can read
  your finances — the same is true of any local finance app.
