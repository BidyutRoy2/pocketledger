"""Rule-based categorisation, with learning from your corrections.

Rules are plain substring matches on the payee (``netflix`` matches
``NETFLIX.COM``). When you re-categorise a transaction, pocketledger can
remember that payee -> category as a rule, so the next import categorises
it automatically. No ML, no cloud: the rules live in your ledger file.
"""

from __future__ import annotations

from .store import Store

# Sensible starting categories. Users can use any category name they like;
# these are only the defaults offered by `categorize --suggest` and docs.
DEFAULT_CATEGORIES = [
    "Housing",
    "Groceries",
    "Dining",
    "Transport",
    "Subscriptions",
    "Entertainment",
    "Health",
    "Shopping",
    "Utilities",
    "Income",
    "Transfer",
    "Other",
]

# Starter rules shipped with `init --starter-rules`. They only fire on
# obvious merchant names; everything else stays Uncategorized on purpose.
STARTER_RULES: list[tuple[str, str]] = [
    ("netflix", "Subscriptions"),
    ("spotify", "Subscriptions"),
    ("youtube premium", "Subscriptions"),
    ("prime video", "Subscriptions"),
    ("disney+", "Subscriptions"),
    ("github", "Subscriptions"),
    ("uber", "Transport"),
    ("lyft", "Transport"),
    ("shell", "Transport"),
    ("bp ", "Transport"),
    ("whole foods", "Groceries"),
    ("walmart", "Groceries"),
    ("tesco", "Groceries"),
    ("aldi", "Groceries"),
    ("mcdonald", "Dining"),
    ("starbucks", "Dining"),
    ("doordash", "Dining"),
    ("ubereats", "Dining"),
    ("amazon", "Shopping"),
    ("electric", "Utilities"),
    ("water bill", "Utilities"),
    ("internet", "Utilities"),
    ("salary", "Income"),
    ("payroll", "Income"),
    ("cvs", "Health"),
    ("pharmacy", "Health"),
    ("gym", "Health"),
]


def install_starter_rules(store: Store) -> int:
    """Add the starter rule set. Returns how many were newly added."""
    added = 0
    for pattern, category in STARTER_RULES:
        before = len(store.list_rules())
        store.add_rule(pattern, category)
        if len(store.list_rules()) > before:
            added += 1
    return added


def categorise_all(store: Store) -> int:
    """Apply rules to every Uncategorized transaction. Returns count changed."""
    changed = 0
    for tx in store.uncategorized():
        category = store.match_rule(tx.payee)
        if category:
            store.set_category(tx.id, category)
            changed += 1
    return changed


def learn_from(store: Store, payee: str, category: str) -> None:
    """Remember a payee -> category mapping as a rule.

    The rule pattern is the payee lowercased, stripped of digits and
    trailing noise (``"NETFLIX.COM 1234"`` -> ``"netflix.com"``). Short
    patterns (< 4 chars) are refused: they would over-match.
    """
    import re

    pattern = re.sub(r"\d+", "", payee.lower()).strip(" .-*#")
    pattern = re.sub(r"\s+", " ", pattern)
    if len(pattern) < 4:
        raise ValueError(f"payee {payee!r} is too short to learn a rule from")
    store.add_rule(pattern, category)
