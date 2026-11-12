# Categories & rules

## How it works

A rule is a plain substring match on the payee: the rule `netflix` matches
`NETFLIX.COM`, `Netflix 1234`, and `NETFLIX.COM*US`. When several rules
match, the **longest pattern wins** (`netflix.com` beats `netflix`).

Rules are applied at import time and by `pocketledger categorize`, which
re-applies them to every `Uncategorized` transaction.

## Starter rules

`init --starter-rules` installs 27 rules for common merchants
(Netflix, Spotify, Uber, Whole Foods, Starbucks, salary, …). They only
fire on obvious merchant names; everything else stays `Uncategorized`
on purpose — a wrong category is worse than none.

## Teaching the ledger

```bash
# Correct one transaction's category and remember it as a rule
pocketledger categorize --learn "Corner Bakery" Dining

# Manage rules directly
pocketledger rule add "corner bakery" Dining
pocketledger rule list
pocketledger rule delete 3
```

`--learn` strips digits and trailing noise from the payee
(`NETFLIX.COM 1234` → `netflix.com`) and refuses patterns shorter than
4 characters, so a rule can never over-match the whole ledger.

## Default categories

Housing, Groceries, Dining, Transport, Subscriptions, Entertainment,
Health, Shopping, Utilities, Income, Transfer, Other. Any category name
works — these are only the suggested defaults.
