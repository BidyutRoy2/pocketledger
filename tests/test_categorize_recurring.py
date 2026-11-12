"""Tests for categorisation learning and recurring-charge detection."""

import os
import tempfile
import unittest

from pocketledger.categorize import categorise_all, install_starter_rules, learn_from
from pocketledger.recurring import detect_recurring, normalise_payee
from pocketledger.store import Store


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "ledger.db"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()


class TestStarterRules(LedgerTestCase):
    def test_install_and_categorise(self):
        added = install_starter_rules(self.store)
        self.assertGreater(added, 10)
        self.store.add_transaction("2026-11-01", -1549, "NETFLIX.COM")
        self.store.add_transaction("2026-11-02", -475, "STARBUCKS #123")
        changed = categorise_all(self.store)
        self.assertEqual(changed, 2)
        cats = {t.payee: t.category for t in self.store.list_transactions()}
        self.assertEqual(cats["NETFLIX.COM"], "Subscriptions")
        self.assertEqual(cats["STARBUCKS #123"], "Dining")

    def test_install_twice_is_idempotent(self):
        install_starter_rules(self.store)
        added = install_starter_rules(self.store)
        self.assertEqual(added, 0)


class TestLearnFrom(LedgerTestCase):
    def test_learn_and_apply(self):
        self.store.add_transaction("2026-11-01", -1200, "Corner Bakery")
        self.store.add_transaction("2026-11-05", -1300, "Corner Bakery")
        learn_from(self.store, "Corner Bakery", "Dining")
        changed = categorise_all(self.store)
        self.assertEqual(changed, 2)

    def test_learn_strips_digits(self):
        learn_from(self.store, "NETFLIX.COM 1234", "Subscriptions")
        self.assertEqual(self.store.match_rule("netflix.com 9999"), "Subscriptions")

    def test_too_short_payee_refused(self):
        with self.assertRaises(ValueError):
            learn_from(self.store, "AB", "Other")


class TestNormalisePayee(unittest.TestCase):
    def test_strips_digits_and_suffix(self):
        self.assertEqual(normalise_payee("NETFLIX.COM 1234"), "netflix")
        self.assertEqual(normalise_payee("Uber *Trip"), "uber trip")

    def test_empty_after_strip(self):
        self.assertEqual(normalise_payee("1234"), "")


class TestRecurring(LedgerTestCase):
    def _add_monthly(self, payee, amount, start="2026-08-15", months=4):
        year, month, day = (int(x) for x in start.split("-"))
        for i in range(months):
            m = month + i
            y = year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            self.store.add_transaction(f"{y:04d}-{m:02d}-{day:02d}", amount, payee)

    def test_detects_monthly_subscription(self):
        self._add_monthly("NETFLIX.COM", -1549)
        found = detect_recurring(self.store)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].payee, "netflix")
        self.assertEqual(found[0].occurrences, 4)
        self.assertEqual(found[0].monthly_cost_minor, 1549)

    def test_ignores_one_offs(self):
        self.store.add_transaction("2026-11-01", -5000, "One Off Shop")
        self.store.add_transaction("2026-11-02", -5000, "One Off Shop")
        self.assertEqual(detect_recurring(self.store), [])

    def test_ignores_irregular_amounts(self):
        # Same payee, different amounts each time -> not recurring.
        self.store.add_transaction("2026-08-01", -1000, "Irregular Shop")
        self.store.add_transaction("2026-09-01", -2500, "Irregular Shop")
        self.store.add_transaction("2026-10-01", -1800, "Irregular Shop")
        self.assertEqual(detect_recurring(self.store), [])

    def test_weekly_charge_monthly_estimate(self):
        from datetime import date, timedelta

        start = date(2026, 10, 1)
        for week in range(6):
            day = start + timedelta(days=week * 7)
            self.store.add_transaction(day.isoformat(), -700, "Weekly Gym")
        found = detect_recurring(self.store)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].monthly_cost_minor, 2800)

    def test_groups_merchant_variants(self):
        self.store.add_transaction("2026-08-15", -1549, "NETFLIX.COM")
        self.store.add_transaction("2026-09-15", -1549, "Netflix 1234")
        self.store.add_transaction("2026-10-15", -1549, "NETFLIX.COM")
        found = detect_recurring(self.store)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].occurrences, 3)


if __name__ == "__main__":
    unittest.main()
