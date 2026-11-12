# Contributing to pocketledger

Thanks for helping make personal finance private again. pocketledger is
small on purpose — zero dependencies, standard library only — and
contributions should keep it that way.

## How to contribute

1. Fork the repo and create a branch: `git checkout -b fix/short-description`.
2. Make your change. Add or update tests for it.
3. Run the full suite: `python -m unittest discover -s tests -v`
4. Run the demo end to end: `bash examples/demo.sh`
5. Open a pull request and fill in the template.

## Rules of the project

- **Zero dependencies.** No new third-party packages, ever. The standard
  library is the whole dependency tree.
- **Money is integer cents, never floats.** Every new amount path needs a
  test that proves rounding is exact (see `tests/test_money.py`).
- **Local-first is non-negotiable.** No network calls, no telemetry, no
  account, no cloud sync. A feature that phones home does not belong here.
- **No placeholder stubs.** Code that ships must actually run.
- **Be honest about limits.** Recurring detection is heuristic, date
  parsing assumes DD/MM for ambiguous dates. If a change affects what is
  (or is not) detected, update `docs/limits.md` and say so in the PR.
- **No financial advice.** pocketledger reports what you spent; it never
  tells you what to buy, sell, or invest in. Keep it that way.

## Reporting security issues

Do **not** open a public issue for a vulnerability. See `SECURITY.md`.

## Code style

- Python 3.11+, 4-space indent, type hints on public functions.
- Keep modules small and single-purpose (`money.py` parses money,
  `csvimport.py` imports CSVs, `recurring.py` detects subscriptions).
- Prefer clear error messages over clever code — the user reading the
  terminal is often mid-budget.
