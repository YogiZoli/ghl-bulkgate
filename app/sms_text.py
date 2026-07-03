"""SMS encoding helpers: GSM-7 vs UCS-2 detection and segment counting.

Hungarian text uses accented characters (á é í ó ö ő ú ü ű). Some of these are
NOT in the GSM 03.38 7-bit alphabet, which forces the whole message to UCS-2
(Unicode) and changes the per-segment character budget. We detect this so we can
set Bulkgate's ``unicode`` flag correctly and log accurate segment counts.
"""
from __future__ import annotations

# GSM 03.38 basic character set + basic extension table.
_GSM7_BASIC = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
_GSM7_EXT = "^{}\\[~]|€"
_GSM7_CHARS = set(_GSM7_BASIC) | set(_GSM7_EXT)


def is_gsm7(text: str) -> bool:
    """True if every character is representable in GSM-7 (so no Unicode needed)."""
    return all(ch in _GSM7_CHARS for ch in text)


def needs_unicode(text: str) -> bool:
    """Inverse of :func:`is_gsm7` — True when UCS-2/Unicode is required."""
    return not is_gsm7(text)


def segment_count(text: str) -> int:
    """Number of SMS segments the message will be split into.

    GSM-7:   160 chars single / 153 per part when concatenated.
    UCS-2:    70 chars single /  67 per part when concatenated.
    Extension-table GSM-7 chars (``^{}\\[~]|€``) count as 2 septets.
    """
    if needs_unicode(text):
        length = len(text)
        return 1 if length <= 70 else -(-length // 67)  # ceil

    # GSM-7: extension chars take two septets.
    septets = sum(2 if ch in _GSM7_EXT else 1 for ch in text)
    return 1 if septets <= 160 else -(-septets // 153)  # ceil
