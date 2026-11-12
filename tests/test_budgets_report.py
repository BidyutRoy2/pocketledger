"""Tests for budgets and reports."""

import os
import tempfile
import unittest

from pocketledger.budgets import budget_statuses
from pocketledger.report import build_report, render_html, render_markdown
from pocketledger.store import Store


class ReportTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "ledger.db"))
        self.store.add_transaction("2026-11-01", 300000, "Acme Salary", "Income")
        self.store.add_transaction("2026-11-02", -8200, "Whole Foods", "Groceries")
        self.store.add_transaction("2026-11-05", -1549, "Netflix", "Subscriptions")
        self.store.add_transaction("2026-11-10", -475, "Starbucks", "Dining")
        self.store.set_budget("Groceries", "2026-11", 40000)
        self.store.set_budget("Dining", "2026-11", 400)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()


class TestBudgets(ReportTestCase):
    def test_status_ok(self):
        statuses = {b.category: b for b in budget_statuses(self.store, "2026-11")}
        self.assertEqual(statuses["Groceries"].status, "OK")
        self.assertEqual(statuses["Groceries"].spent_minor, 8200)
        self.assertEqual(statuses["Groceries"].remaining_minor, 40000 - 8200)

    def test_status_over(self):
        statuses = {b.category: b for b in budget_statuses(self.store, "2026-11")}
        self.assertEqual(statuses["Dining"].status, "OVER")
        self.assertAlmostEqual(statuses["Dining"].pct_used, 118.75)

    def test_watch_band(self):
        self.store.set_budget("Subscriptions", "2026-11", 1800)
        statuses = {b.category: b for b in budget_statuses(self.store, "2026-11")}
        self.assertEqual(statuses["Subscriptions"].status, "WATCH")

    def test_no_budgets_empty(self):
        self.assertEqual(budget_statuses(self.store, "2026-10"), [])


class TestReport(ReportTestCase):
    def test_totals_and_savings_rate(self):
        report = build_report(self.store, "2026-11")
        self.assertEqual(report.income_minor, 300000)
        self.assertEqual(report.spending_minor, 8200 + 1549 + 475)
        self.assertEqual(report.savings_minor, 300000 - 10224)
        self.assertAlmostEqual(report.savings_rate, 96.59, places=1)

    def test_empty_month(self):
        report = build_report(self.store, "2026-01")
        self.assertEqual(report.income_minor, 0)
        self.assertEqual(report.savings_rate, 0.0)

    def test_markdown_contains_figures(self):
        report = build_report(self.store, "2026-11")
        md = render_markdown(self.store, report)
        self.assertIn("$3,000.00", md)
        self.assertIn("Groceries", md)
        self.assertIn("OVER", md)

    def test_html_is_self_contained(self):
        report = build_report(self.store, "2026-11")
        html_doc = render_html(self.store, report)
        self.assertIn("<!doctype html>", html_doc)
        self.assertIn("Groceries", html_doc)
        self.assertIn("$3,000.00", html_doc)
        self.assertNotIn("http://", html_doc)
        self.assertNotIn("https://", html_doc)


if __name__ == "__main__":
    unittest.main()
