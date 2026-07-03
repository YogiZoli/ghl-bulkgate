"""Hungarian phone normalization tests."""
import pytest

from app.phone import InvalidPhoneNumber, normalize, to_plus


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+36301234567", "36301234567"),
        ("0036301234567", "36301234567"),
        ("06301234567", "36301234567"),
        ("36301234567", "36301234567"),
        ("301234567", "36301234567"),
        ("+36 30 123 4567", "36301234567"),
        ("06-30-123-4567", "36301234567"),
        ("(+36) 30/123 45 67", "36301234567"),
    ],
)
def test_normalize_hu(raw, expected):
    assert normalize(raw, "hu") == expected


def test_to_plus():
    assert to_plus("06301234567", "hu") == "+36301234567"


def test_other_country_passthrough_with_plus():
    # Already international with '+': trust it regardless of default country.
    assert normalize("+447911123456", "hu") == "447911123456"


@pytest.mark.parametrize("bad", ["", "   ", "abc", "12", "+", "++//"])
def test_invalid_numbers_raise(bad):
    with pytest.raises(InvalidPhoneNumber):
        normalize(bad, "hu")
