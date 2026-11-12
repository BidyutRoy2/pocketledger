"""Tests for the SQLite store."""

import os
import tempfile
import unittest

from pocketledger.store import Store, fingerprint


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "ledger.db"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()


class TestAccounts(StoreTestCase):
    def test_add_and_list(self):
        self.store.add_account("Main Checking", kind="checking", currency="USD")
        self.store.add_account("Savings", kind="savings")
        accounts = self.store.list_accounts()
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0]["name"], "Main Checking")

    def test_get_account(self):
        self.store.add_account("Cash")
        self.assertIsNotNone(self.store.get_account("Cash"))
        self.assertIsNone(self.store.get_account("Nope"))

    def test_duplicate_name_rejected(self):
        self.store.add_account("Cash")
        with self.assertRaises(Exception):
            self.store.add_account("Cash")


class TestTransactions(StoreTestCase):
    def test_add_and_list(self):
        self.store.add_transaction("2026-11-01", -1250, "Whole Foods", "Groceries")
        self.store.add_transaction("2026-11-02", 300000, "Acme Salary", "Income")
        txs = self.store.list_transactions()
        self.assertEqual(len(txs), 2)
        self.assertEqual(txs[0].payee, "Acme Salary")  # newest first

    def test_duplicate_skipped(self):
        _id, ok1 = self.store.add_transaction("2026-11-01", -1250, "Whole Foods", "Groceries")
        _id, ok2 = self.store.add_transaction("2026-11-01", -1250, "whole foods", "Groceries")
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertEqual(self.store.count_transactions(), 1)

    def test_same_amount_different_payee_is_not_duplicate(self):
        self.store.add_transaction("2026-11-01", -1250, "Whole Foods", "Groceries")
        _id, ok = self.store.add_transaction("2026-11-01", -1250, "Trader Joes", "Groceries")
        self.assertTrue(ok)

    def test_month_totals(self):
        self.store.add_transaction("2026-11-01", -1250, "Shop", "Groceries")
        self.store.add_transaction("2026-11-02", 300000, "Salary", "Income")
        self.store.add_transaction("2026-10-15", -9999, "Old", "Shopping")
        income, spending = self.store.month_totals("2026-11")
        self.assertEqual((income, spending), (300000, 1250))

    def test_sum_by_category(self):
        self.store.add_transaction("2026-11-01", -1250, "Shop A", "Groceries")
        self.store.add_transaction("2026-11-03", -2500, "Shop B", "Groceries")
        self.store.add_transaction("2026-11-05", -900, "Cafe", "Dining")
        rows = {r["category"]: (r["n"], r["total"]) for r in self.store.sum_by_category("2026-11")}
        self.assertEqual(rows["Groceries"], (2, -3750))
        self.assertEqual(rows["Dining"], (1, -900))

    def test_uncategorized_and_set_category(self):
        self.store.add_transaction("2026-11-01", -1250, "Mystery Shop")
        self.assertEqual(len(self.store.uncategorized()), 1)
        tx = self.store.uncategorized()[0]
        self.store.set_category(tx.id, "Shopping")
        self.assertEqual(len(self.store.uncategorized()), 0)

    def test_top_payees(self):
        for _ in range(3):
            self.store.add_transaction("2026-11-01", -1000, "Daily Coffee", "Dining")
        self.store.add_transaction("2026-11-02", -5000, "Big Store", "Shopping")
        top = self.store.top_payees("2026-11")
        self.assertEqual(top[0]["payee"], "Big Store")
        self.assertEqual(top[0]["total"], -5000)


class TestRules(StoreTestCase):
    def test_match_longest_wins(self):
        self.store.add_rule("netflix", "Subscriptions")
        self.store.add_rule("netflix.com", "Streaming")
        self.assertEqual(self.store.match_rule("NETFLIX.COM charge"), "Streaming")

    def test_no_match(self):
        self.assertIsNone(self.store.match_rule("Unknown Shop"))

    def test_delete_rule(self):
        rid = self.store.add_rule("uber", "Transport")
        self.assertTrue(self.store.delete_rule(rid))
        self.assertFalse(self.store.delete_rule(rid))


class TestBudgetsAndBalances(StoreTestCase):
    def test_budget_upsert(self):
        self.store.set_budget("Groceries", "2026-11", 40000)
        self.store.set_budget("Groceries", "2026-11", 50000)
        budgets = self.store.list_budgets("2026-11")
        self.assertEqual(len(budgets), 1)
        self.assertEqual(budgets[0]["limit_minor"], 50000)

    def test_net_worth_latest_snapshot(self):
        acc = self.store.add_account("Checking")
        self.store.set_balance(acc, "2026-11-01", 100000)
        self.store.set_balance(acc, "2026-11-10", 120000)
        rows = self.store.net_worth()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["balance_minor"], 120000)

    def test_net_worth_as_of_date(self):
        acc = self.store.add_account("Checking")
        self.store.set_balance(acc, "2026-11-01", 100000)
        self.store.set_balance(acc, "2026-11-10", 120000)
        rows = self.store.net_worth("2026-11-05")
        self.assertEqual(rows[0]["balance_minor"], 100000)


class TestFingerprint(unittest.TestCase):
    def test_stable_and_case_insensitive(self):
        a = fingerprint("2026-11-01", -1250, "Whole Foods", None)
        b = fingerprint("2026-11-01", -1250, "whole foods", None)
        self.assertEqual(a, b)

    def test_differs_by_amount(self):
        a = fingerprint("2026-11-01", -1250, "Shop", None)
        b = fingerprint("2026-11-01", -1251, "Shop", None)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
