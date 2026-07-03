"""GSM-7 vs UCS-2 detection and segmentation tests."""
from app.sms_text import needs_unicode, segment_count


def test_plain_ascii_is_gsm7():
    assert needs_unicode("Hello world") is False


def test_hungarian_accents_force_unicode():
    # 'ő' and 'ű' are NOT in the GSM-7 alphabet (unlike ä/ö/ü/é which are).
    assert needs_unicode("Időről időre tűz") is True
    assert needs_unicode("hosszú őrző") is True


def test_basic_accents_stay_gsm7():
    # ä, ö, ü, é etc. ARE in GSM-7.
    assert needs_unicode("Schön é à ñ Ä Ö Ü") is False


def test_segment_count_gsm7_single():
    assert segment_count("a" * 160) == 1
    assert segment_count("a" * 161) == 2


def test_segment_count_unicode_single():
    text = "ő" * 70
    assert segment_count(text) == 1
    assert segment_count("ő" * 71) == 2


def test_extension_chars_count_double():
    assert segment_count("€" * 80) == 1
    assert segment_count("€" * 81) == 2
