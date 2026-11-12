# Security Policy

## What pocketledger is — and is not

pocketledger is a **local-first personal finance ledger**: your transactions
live in a SQLite file on your own disk. It makes **no network calls at
all** — no telemetry, no sync, no update checks. There is no server side
to breach and no account to steal.

That also means **your ledger file is only as safe as your disk**. Anyone
who can read `ledger.db` can read your finances. Keep it on an encrypted
disk, back it up encrypted, and do not paste it into issues, chats, or
AI tools.

pocketledger is **not** financial advice, tax software, or a bank. It
reports what you spent; it never tells you what to buy, sell, or invest
in. Amounts are exact integer cents, but bank CSVs can be wrong — check
`pocketledger doctor` output and your statements.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a vulnerability

**Do not open a public issue.** Instead:

1. Open a [private security advisory](https://github.com/BidyutRoy2/pocketledger/security/advisories/new)
   on this repository, or email the maintainer via their GitHub profile.
2. Describe the flaw, with a minimal reproduction if you can.
3. We will confirm receipt within 7 days and aim to ship a fix within
   30 days.

## What counts as a vulnerability here

- pocketledger making any network request, or sending data anywhere.
- An import that writes outside the ledger directory.
- A crafted CSV that executes code or corrupts the ledger beyond the
  imported rows.

## What does not count

- Someone with read access to your machine reading your ledger file —
  that is what file permissions and disk encryption are for.
- A bank CSV with wrong amounts — that is the bank's data, not a bug
  (but do report it if pocketledger mis-parses a valid CSV).
