# Quickstart

```bash
# 1. Install from source (the package is not on PyPI yet)
git clone https://github.com/BidyutRoy2/pocketledger.git
cd pocketledger
python3 -m pip install -e .

# 2. Create a ledger with a first account and starter rules
pocketledger init --account Main --starter-rules

# 3. Import a bank CSV (see examples/bank-sample-a.csv)
pocketledger import ~/Downloads/bank-statement.csv --account Main

# 4. See where the money went
pocketledger report --month 2026-11

# 5. Find the subscriptions quietly charging you
pocketledger recurring
```

Or run the whole flow on sample data without touching your real bank
files:

```bash
bash examples/demo.sh
```

Your ledger lives in `~/pocketledger/ledger.db` (SQLite). Back it up like
any important file — it is the only copy.
