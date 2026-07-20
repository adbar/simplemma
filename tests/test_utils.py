"""Tests for `simplemma.utils`."""

import unicodedata

import pytest

from simplemma import is_known, lemmatize
from simplemma.utils import (
    apostrophe_variants,
    canonicalize_token,
    has_apostrophe,
    levenshtein_dist,
    normalize_apostrophes,
    normalize_token,
    strip_diacritics,
    validate_lang_input,
)


def test_normalize_token() -> None:
    nfd = unicodedata.normalize("NFD", "Häuser")
    assert nfd != "Häuser"
    assert normalize_token(nfd) == "Häuser"
    assert normalize_token("Häuser") == "Häuser"
    # NFC, not NFKC: compatibility characters are preserved, not folded
    assert normalize_token("ﬁ") == "ﬁ"  # ligature stays, would become "fi" under NFKC


def test_strip_diacritics() -> None:
    assert strip_diacritics("café") == "cafe"
    assert strip_diacritics("señor") == "senor"
    assert strip_diacritics("plain") == "plain"


def test_canonicalize_token() -> None:
    # grc: positional grave -> citation acute (letters, breathing combos, iota subscript)
    assert canonicalize_token("ἐγὼ καὶ δὲ", "grc") == "ἐγώ καί δέ"
    assert canonicalize_token("ἀκούσας", "grc") == "ἀκούσας"  # already acute: no-op
    # he: niqqud/cantillation points stripped (pedagogical, absent from running text)
    assert canonicalize_token("וְהַבַּיִת", "he") == "והבית"
    assert canonicalize_token("והבית", "he") == "והבית"  # already unpointed: no-op
    # ar: tashkeel/dagger-alef/tatweel stripped (same pedagogical-vocalization
    # mismatch); fa shares the script but must be UNAFFECTED (own table key)
    assert canonicalize_token("كِتَابٌ", "ar") == "كتاب"
    assert canonicalize_token("كِتَابٌ", "fa") == "كِتَابٌ"
    # not extended to other languages -- lv macron is orthographic, not positional
    assert canonicalize_token("garā", "lv") == "garā"
    assert canonicalize_token("garā", "en") == "garā"
    assert (
        canonicalize_token("וְהַבַּיִת", "ar") == "וְהַבַּיִת"
    )  # he table not applied elsewhere


def test_canon_langs_disjoint_from_raw_token_strategies() -> None:
    """Affix/rule strategies match the raw token, so canon langs must never
    join AFFIX_LANGS/RULE_FUNCTIONS (see _CANON_TABLES)."""
    from simplemma.strategies.affix_decomposition import AFFIX_LANGS
    from simplemma.strategies.defaultrules import RULE_FUNCTIONS
    from simplemma.utils import _CANON_TABLES

    canon = set(_CANON_TABLES)
    assert canon.isdisjoint(AFFIX_LANGS)
    assert canon.isdisjoint(RULE_FUNCTIONS)


def test_apostrophe_helpers() -> None:
    # all three glyphs (straight U+0027, curly U+2019, modifier U+02BC) fold
    assert normalize_apostrophes("l’a") == normalize_apostrophes("lʼa") == "l'a"
    assert normalize_apostrophes("la") == "la"
    assert has_apostrophe("l'a") and has_apostrophe("l’a") and has_apostrophe("lʼa")
    assert not has_apostrophe("la")
    # variants: apostrophe-free token is returned unchanged; otherwise every glyph
    assert apostrophe_variants("la") == ("la",)
    assert apostrophe_variants("l'a") == ("l'a", "l’a", "lʼa")
    assert apostrophe_variants("l’a") == ("l’a", "l'a", "lʼa")  # typed form first


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
