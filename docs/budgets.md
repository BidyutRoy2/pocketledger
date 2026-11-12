# Budgets

A budget is a monthly spending cap for one category.

```bash
pocketledger budget --set Groceries 400 --month 2026-11
pocketledger budget --month 2026-11
```

```
budgets for 2026-11
Groceries        $151.20 /    $400.00 ███████░░░░░░░░░░░░░    38% OK
Dining            $10.50 /     $60.00 ███░░░░░░░░░░░░░░░░░    18% OK
```

## Status bands

| Status | Meaning |
|---|---|
| OK | Spent under 80% of the cap |
| WATCH | Spent 80–100% — you are close |
| OVER | Spent more than the cap |

Categories without a budget are simply not shown. pocketledger never
nags about categories you did not budget — a budget is a tool you
opt into, not a lecture.

Budgets are per month (`YYYY-MM`). Setting a budget for a new month
starts from zero; copy last month's with `pocketledger budget --set`
again, or wait for the planned `budget copy` command.
