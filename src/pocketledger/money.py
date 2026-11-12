"""Money parsing and formatting.

All amounts are stored as integer minor units (cents) in the database so
sums are exact. Display uses Decimal only for formatting. No floats are
ever used for money math.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Matches things like "1,234.56", "-42", "($12.34)", "£9.99", "12,50" (EU).
_AMOUNT_RE = re.compile(r"^[^\d\-+()]*([\-+()]?[\d\s.,']+)[^\d]*$")

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "৳": "BDT"}


class MoneyError(ValueError):
    """Raised when a string cannot be parsed as an amount of money."""


def parse_amount(text: str, *, currency: str = "USD") -> tuple[int, str]:
    """Parse a human-written amount into (minor_units, currency).

    Accepts optional currency symbols, thousands separators, parentheses
    for negatives, and a leading minus. ``"1,234.56"`` -> ``(123456, "USD")``.
    ``"($12.34)"`` -> ``(-1234, "USD")``. A trailing/leading symbol such as
    ``€`` or ``৳`` overrides the currency.
    """
    if text is None:
        raise MoneyError("amount is empty")
    raw = str(text).strip()
    if not raw:
        raise MoneyError("amount is empty")

    detected = currency
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in raw:
            detected = code
            raw = raw.replace(symbol, "")
            break

    negative = False
    raw = raw.strip()
    if raw.startswith("(") and raw.endswith(")"):
        negative = True
        raw = raw[1:-1].strip()
    if raw.startswith("-"):
        negative = True
        raw = raw[1:]
    elif raw.startswith("+"):
        raw = raw[1:]
    raw = raw.replace(" ", "").replace("'", "")

    # Decide the decimal separator: the last of "," or "." wins when both
    # appear; a lone "," with exactly two digits after it is a decimal
    # separator (European style), otherwise it is a thousands separator.
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        head, _, tail = raw.rpartition(",")
        if len(tail) == 2 and head:
            raw = head + "." + tail
        else:
            raw = raw.replace(",", "")

    if not re.fullmatch(r"\d+(\.\d+)?", raw):
        raise MoneyError(f"cannot parse amount: {text!r}")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise MoneyError(f"cannot parse amount: {text!r}") from exc
    cents = int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if negative:
        cents = -cents
    return cents, detected


def format_amount(minor: int, currency: str = "USD") -> str:
    """Format integer minor units as a readable amount, e.g. ``-$12.34``."""
    sign = "-" if minor < 0 else ""
    whole, cents = divmod(abs(minor), 100)
    whole_str = f"{whole:,}"
    symbol = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "INR": "₹", "BDT": "৳"}.get(
        currency, ""
    )
    if symbol:
        return f"{sign}{symbol}{whole_str}.{cents:02d}"
    return f"{sign}{whole_str}.{cents:02d} {currency}"


def format_signed(minor: int, currency: str = "USD") -> str:
    """Format with an explicit ``+``/``-`` sign (used in reports)."""
    if minor >= 0:
        return "+" + format_amount(minor, currency)
    return format_amount(minor, currency)
