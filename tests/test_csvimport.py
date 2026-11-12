"""Tests for CSV import and date normalisation."""

import os
import tempfile
import unittest

from pocketledger.csvimport import detect_columns, import_csv, normalise_date
from pocketledger.store import Store

BANK_A = """Date,Description,Amount
2026-11-01,NETFLIX.COM,-15.49
2026-11-02,Whole Foods Market,-82.30
2026-11-03,ACME SALARY,3200.00
"""

BANK_B = """Transaction Date,Merchant,Debit,Credit
01/11/2026,STARBUCKS,4.75,
02/11/2026,UBER,12.40,
03/11/2026,ACME PAYROLL,,3200.00
"""

BANK_NO_HEADER = """2026-11-01,Corner Shop,-25.00
2026-11-02,Corner Shop,-25.00
"""


class ImportTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "ledger.db"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()


class TestNormaliseDate(unittest.TestCase):
    def test_iso(self):
        self.assertEqual(normalise_date("2026-11-10"), "2026-11-10")

    def test_dd_mm_yyyy_slash(self):
        self.assertEqual(normalise_date("10/11/2026"), "2026-11-10")

    def test_mm_dd_yyyy_unambiguous(self):
        # 11/25/2026 can only be MM/DD/YYYY
        self.assertEqual(normalise_date("11/25/2026"), "2026-11-25")

    def test_dd_mm_yyyy_unambiguous(self):
        # 25/11/2026 can only be DD/MM/YYYY
        self.assertEqual(normalise_date("25/11/2026"), "2026-11-25")

    def test_dotted(self):
        self.assertEqual(normalise_date("10.11.2026"), "2026-11-10")

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            normalise_date("yesterday")


class TestDetectColumns(unittest.TestCase):
    def test_standard(self):
        cols = detect_columns(["Date", "Description", "Amount"])
        self.assertEqual(cols, {"date": 0, "payee": 1, "amount": 2})

    def test_split_debit_credit(self):
        cols = detect_columns(["Transaction Date", "Merchant", "Debit", "Credit"])
        self.assertEqual(cols["debit"], 2)
        self.assertEqual(cols["credit"], 3)


class TestImportCsv(ImportTestCase):
    def test_bank_a(self):
        result = import_csv(self.store, BANK_A)
        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped_duplicates, 0)
        self.assertEqual(self.store.count_transactions(), 3)
        income, spending = self.store.month_totals("2026-11")
        self.assertEqual(income, 320000)
        self.assertEqual(spending, 1549 + 8230)

    def test_bank_b_split_columns(self):
        result = import_csv(self.store, BANK_B)
        self.assertEqual(result.imported, 3)
        txs = self.store.list_transactions()
        by_payee = {t.payee: t.amount_minor for t in txs}
        self.assertEqual(by_payee["STARBUCKS"], -475)
        self.assertEqual(by_payee["ACME PAYROLL"], 320000)

    def test_reimport_is_all_duplicates(self):
        import_csv(self.store, BANK_A)
        result = import_csv(self.store, BANK_A)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.skipped_duplicates, 3)
        self.assertEqual(self.store.count_transactions(), 3)

    def test_bad_rows_skipped(self):
        bad = BANK_A + "not-a-date,Broken Row,xyz\n"
        result = import_csv(self.store, bad)
        self.assertEqual(result.imported, 3)
        self.assertEqual(result.skipped_bad_rows, 1)
        self.assertTrue(result.errors)

    def test_no_header_positional(self):
        result = import_csv(self.store, BANK_NO_HEADER)
        self.assertEqual(result.imported, 2)
        self.assertEqual(self.store.count_transactions(), 2)

    def test_rules_applied_on_import(self):
        self.store.add_rule("netflix", "Subscriptions")
        import_csv(self.store, BANK_A)
        txs = [t for t in self.store.list_transactions() if "NETFLIX" in t.payee]
        self.assertEqual(txs[0].category, "Subscriptions")

    def test_empty_file(self):
        result = import_csv(self.store, "")
        self.assertEqual(result.imported, 0)
        self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
