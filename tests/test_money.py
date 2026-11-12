"""Tests for money parsing and formatting."""

import unittest

from pocketledger.money import MoneyError, format_amount, format_signed, parse_amount


class TestParseAmount(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_amount("12.50"), (1250, "USD"))

    def test_integer(self):
        self.assertEqual(parse_amount("42"), (4200, "USD"))

    def test_thousands_separator(self):
        self.assertEqual(parse_amount("1,234.56"), (123456, "USD"))

    def test_negative(self):
        self.assertEqual(parse_amount("-42.00"), (-4200, "USD"))

    def test_parentheses_negative(self):
        self.assertEqual(parse_amount("($12.34)"), (-1234, "USD"))

    def test_currency_symbol(self):
        self.assertEqual(parse_amount("€9.99"), (999, "EUR"))
        self.assertEqual(parse_amount("£5"), (500, "GBP"))
        self.assertEqual(parse_amount("৳100.50"), (10050, "BDT"))

    def test_european_decimal(self):
        self.assertEqual(parse_amount("12,50"), (1250, "USD"))

    def test_european_thousands(self):
        self.assertEqual(parse_amount("1.234,56"), (123456, "USD"))

    def test_rounding_half_up(self):
        self.assertEqual(parse_amount("0.005"), (1, "USD"))

    def test_empty_raises(self):
        with self.assertRaises(MoneyError):
            parse_amount("")

    def test_garbage_raises(self):
        with self.assertRaises(MoneyError):
            parse_amount("abc")

    def test_currency_param(self):
        self.assertEqual(parse_amount("10", currency="EUR"), (1000, "EUR"))


class TestFormatAmount(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(format_amount(1250), "$12.50")

    def test_negative(self):
        self.assertEqual(format_amount(-4200), "-$42.00")

    def test_thousands(self):
        self.assertEqual(format_amount(123456), "$1,234.56")

    def test_zero(self):
        self.assertEqual(format_amount(0), "$0.00")

    def test_other_currency(self):
        self.assertEqual(format_amount(999, "EUR"), "€9.99")
        self.assertEqual(format_amount(10050, "BDT"), "৳100.50")

    def test_signed(self):
        self.assertEqual(format_signed(500), "+$5.00")
        self.assertEqual(format_signed(-500), "-$5.00")


if __name__ == "__main__":
    unittest.main()
