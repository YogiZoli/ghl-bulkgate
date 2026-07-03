"""Opt-out keyword detection for EU SMS compliance.

When an inbound SMS body is just an unsubscribe keyword, we flag the contact as
opted-out and stop sending. A re-subscribe keyword clears the flag.
"""
from __future__ import annotations

# Stop sending if the (trimmed, upper-cased) inbound body equals one of these.
STOP_KEYWORDS = {
    "STOP",
    "STOPP",
    "LEIRATKOZAS",
    "LEIRATKOZÁS",
    "LEIRAT",
    "UNSUBSCRIBE",
    "CANCEL",
    "END",
    "QUIT",
}

# Re-subscribe keywords (clear the opt-out flag).
START_KEYWORDS = {
    "START",
    "FELIRATKOZAS",
    "FELIRATKOZÁS",
    "UNSTOP",
}

# NOTE: plain conversational words ("NEM", "IGEN", "YES") are deliberately NOT
# keywords — in a two-way GHL conversation a simple "Nem" reply must not
# unsubscribe the contact.


def _norm(body: str) -> str:
    return (body or "").strip().upper()


def is_stop(body: str) -> bool:
    return _norm(body) in STOP_KEYWORDS


def is_start(body: str) -> bool:
    return _norm(body) in START_KEYWORDS
