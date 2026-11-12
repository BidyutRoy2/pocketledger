#!/usr/bin/env bash
# pocketledger demo — runs the full flow on the sample CSVs.
# Usage: bash examples/demo.sh   (needs python3; no install required)
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src"

LEDGER="/tmp/pocketledger-demo"
rm -rf "$LEDGER"

echo "== init =="
python3 -m pocketledger --ledger "$LEDGER" init --account Main --starter-rules
echo
echo "== import bank A (Date/Description/Amount) =="
python3 -m pocketledger --ledger "$LEDGER" import examples/bank-sample-a.csv --account Main
echo
echo "== import bank B (split Debit/Credit, DD/MM/YYYY) =="
python3 -m pocketledger --ledger "$LEDGER" import examples/bank-sample-b.csv --account Main
echo
echo "== budgets =="
python3 -m pocketledger --ledger "$LEDGER" budget --set Groceries 400 --month 2026-11
python3 -m pocketledger --ledger "$LEDGER" budget --set Dining 60 --month 2026-11
python3 -m pocketledger --ledger "$LEDGER" budget --month 2026-11
echo
echo "== report =="
python3 -m pocketledger --ledger "$LEDGER" report --month 2026-11
echo
echo "== recurring charges =="
python3 -m pocketledger --ledger "$LEDGER" recurring
echo
echo "== balances / net worth =="
python3 -m pocketledger --ledger "$LEDGER" balance Main 2841.55 --date 2026-11-10
python3 -m pocketledger --ledger "$LEDGER" networth
echo
echo "== doctor (finds 1 uncategorized row) =="
python3 -m pocketledger --ledger "$LEDGER" doctor || true
echo
echo "== teach it: Trader Joe's is Groceries =="
python3 -m pocketledger --ledger "$LEDGER" categorize --learn "Trader Joe's" Groceries
echo
echo "== doctor again =="
python3 -m pocketledger --ledger "$LEDGER" doctor
echo
echo "Demo ledger left at $LEDGER — delete it when done: rm -rf $LEDGER"
