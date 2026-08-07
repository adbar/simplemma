"""Tests for `simplemma.utils`."""

import unicodedata
from collections.abc import Iterable

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
    """Affix/rule/morpheme strategies match the raw token, so canon langs must
    never join AFFIX_LANGS/RULE_FUNCTIONS/MORPHEME_LANGS (see CANON_LANGS)."""
    from simplemma.strategies.affix_decomposition import AFFIX_LANGS
    from simplemma.strategies.defaultrules import RULE_FUNCTIONS
    from simplemma.strategies.morpheme_decomposition import MORPHEME_LANGS
    from simplemma.utils import CANON_LANGS

    assert CANON_LANGS.isdisjoint(AFFIX_LANGS)
    assert CANON_LANGS.isdisjoint(RULE_FUNCTIONS)
    assert CANON_LANGS.isdisjoint(MORPHEME_LANGS)


def test_per_language_tables_reference_supported_languages() -> None:
    """A typo'd language code in a per-language config table fails silently --
    the mechanism just never fires. Explicit register, not auto-discovery."""
    from simplemma.casing import ALLCAPS_KEEP_LANGS, GATED_INITIAL_LOWERING_LANGS
    from simplemma.sentences import _ABBREVS, _STARTERS, _TERMINATORS
    from simplemma.strategies.affix_decomposition import AFFIX_LANGS, GREEDY_EXCLUDE
    from simplemma.strategies.apostrophe_boundary import APOSTROPHE_BOUNDARY_LANGS
    from simplemma.strategies.clitic_decomposition import CLITIC_LANGS, PROCLITIC_LANGS
    from simplemma.strategies.defaultprefixes import DEFAULT_KNOWN_PREFIXES
    from simplemma.strategies.defaultrules import RULE_FUNCTIONS
    from simplemma.strategies.dictionaries.dictionary_factory import (
        SUPPORTED_LANGUAGES,
    )
    from simplemma.strategies.fallback.to_lowercase import BETTER_LOWER
    from simplemma.strategies.greedy_dictionary_lookup import MIN_LENGTH_OVERRIDES
    from simplemma.strategies.morpheme_decomposition import MORPHEME_LANGS
    from simplemma.utils import CANON_LANGS
    from training.build_lang_config import BUILD_NORMALIZATION, JUNK_ENTRY_PREDICATES
    from training.dictionary_builder import (
        FRONTCODE_REVERSE_KEY_LANGS,
        IDENTITY_SOFT_LANGS,
        OVERRIDES_DIR,
        PARADIGM_PRIOR_LANGS,
        V2_FILL_LANGS,
    )
    from training.ud_conllu import DATASET_LANG_OVERRIDES, _GOLD_COMPOUND_SEPARATORS
    from training.wikidata_lexemes import LANGUAGE_QIDS

    tables: dict[str, Iterable[str]] = {
        "ALLCAPS_KEEP_LANGS": ALLCAPS_KEEP_LANGS,
        "GATED_INITIAL_LOWERING_LANGS": GATED_INITIAL_LOWERING_LANGS,
        "_ABBREVS": _ABBREVS,
        "_STARTERS": _STARTERS,
        "_TERMINATORS": [k for k in _TERMINATORS if k is not None],
        "AFFIX_LANGS": AFFIX_LANGS,
        "GREEDY_EXCLUDE": GREEDY_EXCLUDE,
        "APOSTROPHE_BOUNDARY_LANGS": APOSTROPHE_BOUNDARY_LANGS,
        "CLITIC_LANGS": CLITIC_LANGS,
        "PROCLITIC_LANGS": PROCLITIC_LANGS,
        "DEFAULT_KNOWN_PREFIXES": DEFAULT_KNOWN_PREFIXES,
        "RULE_FUNCTIONS": RULE_FUNCTIONS,
        "BETTER_LOWER": BETTER_LOWER,
        "MIN_LENGTH_OVERRIDES": MIN_LENGTH_OVERRIDES,
        "MORPHEME_LANGS": MORPHEME_LANGS,
        "CANON_LANGS": CANON_LANGS,
        "BUILD_NORMALIZATION": BUILD_NORMALIZATION,
        "JUNK_ENTRY_PREDICATES": JUNK_ENTRY_PREDICATES,
        "FRONTCODE_REVERSE_KEY_LANGS": FRONTCODE_REVERSE_KEY_LANGS,
        "IDENTITY_SOFT_LANGS": IDENTITY_SOFT_LANGS,
        "PARADIGM_PRIOR_LANGS": PARADIGM_PRIOR_LANGS,
        "V2_FILL_LANGS": V2_FILL_LANGS,
        "LANGUAGE_QIDS": LANGUAGE_QIDS,
        "_GOLD_COMPOUND_SEPARATORS": _GOLD_COMPOUND_SEPARATORS,
        "DATASET_LANG_OVERRIDES values": DATASET_LANG_OVERRIDES.values(),
        "overrides/*.tsv": [p.stem for p in OVERRIDES_DIR.glob("*.tsv")],
    }
    unknown = {name: set(t) - SUPPORTED_LANGUAGES for name, t in tables.items()}
    assert {name: codes for name, codes in unknown.items() if codes} == {}


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
