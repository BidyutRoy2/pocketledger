"""End-to-end CLI tests (run the real CLI against temp ledgers)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAMPLE_CSV = """Date,Description,Amount
2026-11-01,NETFLIX.COM,-15.49
2026-11-02,Whole Foods Market,-82.30
2026-11-03,ACME SALARY,3200.00
2026-10-15,NETFLIX.COM,-15.49
2026-09-15,NETFLIX.COM,-15.49
2026-08-15,NETFLIX.COM,-15.49
"""


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = os.path.join(self.tmp.name, "ledger")
        self.env = dict(os.environ, PYTHONPATH=str(REPO / "src"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "pocketledger", "--ledger", self.ledger, *args],
            capture_output=True, text=True, env=self.env,
        )

    def test_full_flow(self):
        # init
        r = self.run_cli("init", "--account", "Main", "--starter-rules")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ledger ready", r.stdout)

        # import
        csv_path = os.path.join(self.tmp.name, "bank.csv")
        Path(csv_path).write_text(SAMPLE_CSV)
        r = self.run_cli("import", csv_path, "--account", "Main")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("imported: 6", r.stdout)
        self.assertIn("auto-categorised: 6", r.stdout)

        # re-import dedupes
        r = self.run_cli("import", csv_path, "--account", "Main")
        self.assertIn("skipped duplicates: 6", r.stdout)

        # list
        r = self.run_cli("list", "--month", "2026-11")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("NETFLIX.COM", r.stdout)
        self.assertIn("3 transactions", r.stdout)

        # budget + report
        r = self.run_cli("budget", "--set", "Groceries", "400", "--month", "2026-11")
        self.assertIn("budget set", r.stdout)
        r = self.run_cli("report", "--month", "2026-11")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("$3,200.00", r.stdout)
        self.assertIn("Groceries", r.stdout)

        # recurring finds Netflix
        r = self.run_cli("recurring")
        self.assertIn("netflix", r.stdout.lower())
        self.assertIn("4", r.stdout)

        # balance + networth
        r = self.run_cli("balance", "Main", "2500.00", "--date", "2026-11-10")
        self.assertIn("balance recorded", r.stdout)
        r = self.run_cli("networth")
        self.assertIn("$2,500.00", r.stdout)

        # export json
        r = self.run_cli("export", "--format", "json", "--month", "2026-11")
        data = json.loads(r.stdout)
        self.assertEqual(len(data), 3)

        # doctor clean
        r = self.run_cli("doctor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    def test_add_and_duplicate(self):
        self.run_cli("init", "--account", "Cash")
        r = self.run_cli("add", "--date", "2026-11-05", "--amount", "9.99",
                     "--direction", "out", "--payee", "Corner Shop",
                     "--category", "Shopping", "--account", "Cash")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Corner Shop", r.stdout)
        r = self.run_cli("add", "--date", "2026-11-05", "--amount", "9.99",
                     "--direction", "out", "--payee", "Corner Shop",
                     "--category", "Shopping", "--account", "Cash")
        self.assertEqual(r.returncode, 1)
        self.assertIn("duplicate", r.stdout)

    def test_no_ledger_errors(self):
        r = self.run_cli("list")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no ledger", r.stderr)

    def test_bad_amount_rejected(self):
        self.run_cli("init")
        r = self.run_cli("add", "--amount", "abc", "--payee", "Shop")
        self.assertEqual(r.returncode, 1)
        self.assertIn("error", r.stderr)

    def test_rule_crud(self):
        self.run_cli("init")
        r = self.run_cli("rule", "add", "corner bakery", "Dining")
        self.assertIn("rule added", r.stdout)
        r = self.run_cli("rule", "list")
        self.assertIn("corner bakery", r.stdout)
        r = self.run_cli("rule", "delete", "1")
        self.assertIn("deleted", r.stdout)

    def test_report_html_file(self):
        self.run_cli("init", "--account", "Main", "--starter-rules")
        csv_path = os.path.join(self.tmp.name, "bank.csv")
        Path(csv_path).write_text(SAMPLE_CSV)
        self.run_cli("import", csv_path, "--account", "Main")
        out = os.path.join(self.tmp.name, "report.html")
        r = self.run_cli("report", "--month", "2026-11", "--format", "html", "--output", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        html_text = Path(out).read_text()
        self.assertIn("pocketledger", html_text)
        self.assertIn("$3,200.00", html_text)


if __name__ == "__main__":
    unittest.main()
