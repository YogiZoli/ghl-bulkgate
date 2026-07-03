"""Phone-number normalization to E.164 digits (no leading '+').

Bulkgate's ``number`` field wants international format *without* the plus, e.g.
``36301234567``. GHL hands us numbers in many shapes (``+3630...``, ``0036...``,
``0630...``, bare ``301234567``). This module collapses all of those to the
Bulkgate-friendly digit string and also produces the ``+`` form for GHL/logging.

Defaults assume Hungary (country code 36, trunk prefix 0) but the country code
is configurable so the same logic works for other markets.
"""
from __future__ import annotations

import re

# ISO alpha-2 -> international dialing code + national trunk prefix.
# Extend as needed for additional installer markets.
_COUNTRY_DIAL = {
    "hu": ("36", "06"),
    "cz": ("420", "0"),
    "sk": ("421", "0"),
    "at": ("43", "0"),
    "de": ("49", "0"),
    "gb": ("44", "0"),
    "us": ("1", "1"),
}

_NON_DIGIT = re.compile(r"[^\d+]")


class InvalidPhoneNumber(ValueError):
    """Raised when a number cannot be normalized to a plausible E.164 value."""


def _clean(raw: str) -> str:
    """Strip spaces, dashes, parentheses; keep digits and a single leading '+'."""
    raw = raw.strip()
    plus = raw.startswith("+") or raw.startswith("00")
    digits = _NON_DIGIT.sub("", raw)
    if digits.startswith("+"):
        digits = digits[1:]
        plus = True
    if digits.startswith("00"):
        digits = digits[2:]
        plus = True
    return ("+" if plus else "") + digits


def normalize(raw: str, country: str = "hu") -> str:
    """Return E.164 *digits* (no '+'), e.g. ``"36301234567"``.

    Handles, for HU:
      ``+36 30 123 4567``, ``0036301234567``, ``06301234567``,
      ``36301234567``, ``301234567`` -> ``36301234567``.

    :raises InvalidPhoneNumber: if the result is too short/long to be a number.
    """
    if raw is None:
        raise InvalidPhoneNumber("empty number")

    country = (country or "hu").lower()
    cc, trunk = _COUNTRY_DIAL.get(country, _COUNTRY_DIAL["hu"])

    cleaned = _clean(str(raw))
    had_plus = cleaned.startswith("+")
    digits = cleaned.lstrip("+")

    if not digits:
        raise InvalidPhoneNumber(f"no digits in {raw!r}")

    if had_plus:
        # Already international (the '+'/'00' told us so). Trust it.
        e164 = digits
    elif digits.startswith(cc) and len(digits) >= len(cc) + 6:
        # Already starts with the country code.
        e164 = digits
    elif trunk and digits.startswith(trunk):
        # National form with trunk prefix, e.g. HU "0630..." -> drop "06".
        e164 = cc + digits[len(trunk):]
    else:
        # Bare national subscriber number, e.g. HU "301234567".
        e164 = cc + digits

    if not (8 <= len(e164) <= 15):  # E.164 allows max 15 digits
        raise InvalidPhoneNumber(f"{raw!r} -> {e164!r} has implausible length")
    if not e164.isdigit():
        raise InvalidPhoneNumber(f"{raw!r} produced non-digit result {e164!r}")
    return e164


def to_plus(raw: str, country: str = "hu") -> str:
    """Like :func:`normalize` but returns the ``+`` form (``"+36301234567"``)."""
    return "+" + normalize(raw, country)
