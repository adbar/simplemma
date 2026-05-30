"""Tests for `simplemma.utils`."""

import pytest

from simplemma import is_known
from simplemma.utils import levenshtein_dist, validate_lang_input


def test_validate_lang_input() -> None:
    # a string is wrapped into a one-element tuple
    assert validate_lang_input("en") == ("en",)
    # a tuple is passed through unchanged
    assert validate_lang_input(("de", "en")) == ("de", "en")
    # an empty tuple is passed through unchanged (there is no guard against it;
    # downstream this makes the lemmatizer fallback raise StopIteration on
    # next(iter(lang)))
    assert validate_lang_input(()) == ()
    # non-str / non-tuple inputs raise TypeError. This branch is otherwise
    # never reached through lemmatize(), where an unhashable lang argument
    # fails earlier in the lru_cache rather than in validate_lang_input.
    with pytest.raises(TypeError):
        validate_lang_input(123)  # type: ignore[arg-type]
    # a list is the realistic mistake (mutable, looks tuple-like)
    with pytest.raises(TypeError):
        validate_lang_input(["en"])  # type: ignore[arg-type]
    # end-to-end through is_known(), which validates directly without caching
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
