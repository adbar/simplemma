"""Tests for `simplemma.utils`."""

import unicodedata

import pytest

from simplemma import is_known, lemmatize
from simplemma.utils import levenshtein_dist, normalize_token, validate_lang_input


def test_normalize_token() -> None:
    nfd = unicodedata.normalize("NFD", "Häuser")
    assert nfd != "Häuser"
    assert normalize_token(nfd) == "Häuser"
    assert normalize_token("Häuser") == "Häuser"
    # NFC, not NFKC: compatibility characters are preserved, not folded
    assert normalize_token("ﬁ") == "ﬁ"  # ligature stays, would become "fi" under NFKC


def test_validate_lang_input() -> None:
    assert validate_lang_input("en") == ("en",)
    assert validate_lang_input(("de", "en")) == ("de", "en")
    # empty lang must fail cleanly, not as a downstream StopIteration
    with pytest.raises(ValueError):
        validate_lang_input(())
    with pytest.raises(ValueError):
        lemmatize("test", ())
    with pytest.raises(TypeError):
        validate_lang_input(123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        validate_lang_input(["en"])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        is_known("test", lang=123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "str1,str2,expected",
    [
        ("", "", 0),
        ("abc", "abc", 0),
        ("", "abc", 3),
        ("abc", "", 3),
        ("kitten", "sitting", 3),
        ("flaw", "lawn", 2),
        ("a", "b", 1),
        ("Levenshtein", "Levenstein", 1),
    ],
)
def test_levenshtein_dist(str1: str, str2: str, expected: int) -> None:
    assert levenshtein_dist(str1, str2) == expected
    # the distance is symmetric
    assert levenshtein_dist(str2, str1) == expected
