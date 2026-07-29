"""Tests for the casing decision layer (`simplemma.casing`), exercised without
dictionaries: membership is a plain set probe, decisions are (surface, keep)
pairs. End-to-end coverage through the Lemmatizer lives in test_lemmatizer.py."""

import unicodedata
from collections.abc import Iterator

from simplemma.casing import (
    GATED_INITIAL_LOWERING_LANGS,
    SENTENCE_BUFFER_CAP,
    MembershipCheck,
    SentenceCasing,
    is_keepable_allcaps,
    is_sentence_boundary,
)
from simplemma.strategies.fallback.to_lowercase import BETTER_LOWER


def _member_of(words: set[str]) -> MembershipCheck:
    return lambda token, _lang: token in words


def test_gated_langs_disjoint_from_fallback_lowering() -> None:
    """A language the fallback already lowercases must not also be gated:
    the two per-language casing policies would conflict."""

    assert GATED_INITIAL_LOWERING_LANGS.isdisjoint(BETTER_LOWER)


def test_sentence_boundary_detects_collapsed_runs() -> None:
    """Buffered-path boundary: first char, so collapsed runs ('...', '!!')
    match but alnum-final tokens ('.270') don't."""

    for term in [".", "?", "!", "…", "։", "...", "!!", "??", "?!"]:
        assert is_sentence_boundary(term), term
    for other in ["hello", "3.14", ".270", "l'homme", ""]:
        assert not is_sentence_boundary(other), other


def test_keepable_allcaps_excludes_long_roman_numerals() -> None:
    """The Roman-numeral exclusion applies only to 3+ char numerals; 2-char
    tokens (CD/DC/MM/XL) stay keepable as acronyms."""

    for acronym in ["CD", "DC", "MM", "MI", "MC", "XL", "XX", "USB", "SQL"]:
        assert is_keepable_allcaps(acronym), acronym
    for numeral in ["XII", "XIV", "MCM", "MIX", "MMXX"]:
        assert not is_keepable_allcaps(numeral), numeral


def test_streaming_path_keeps_legacy_boundary() -> None:
    """Streaming path must NOT reset after collapsed runs ('...') -- widening it
    is UD-measured harmful; guards the revert (see casing._streaming)."""

    casing = SentenceCasing("fr", None)
    # 'Fin' initial -> lowered; '...' does not reset; 'Alain' stays capitalized
    surfaces = [s for s, _keep in casing.apply(iter(["Fin", "...", "Alain"]))]
    assert surfaces == ["fin", "...", "Alain"]


def test_gated_initial_surface() -> None:
    """Gated initial-lowering: dictionary members and all-caps forms are
    lowered, unknown capitalized words (probable proper nouns) are kept."""

    casing = SentenceCasing("en", _member_of({"the"}))
    assert casing.initial_surface("The") == "the"  # dict member -> lowered
    assert casing.initial_surface("Iran") == "Iran"  # not a member -> kept
    assert casing.initial_surface("NASA") == "nasa"  # all-caps: lookup recovers


def test_acronym_keep_decisions() -> None:
    """Mid-sentence ALL-CAPS kept verbatim; sentence-initial ALL-CAPS defers
    to the D' gate when its lowercase form is a dictionary entry."""

    casing = SentenceCasing("de", _member_of({"mit"}))
    out = list(casing.apply(iter(["Die", "Firma", "MIT", "."])))
    assert ("MIT", True) in out
    out = list(casing.apply(iter(["MIT", "dem", "Auto", "."])))
    assert out[0] == ("mit", False)


def test_shouting_ratio_leave_one_out() -> None:
    """A lone acronym isn't 'shouting'; a majority-shouted sentence turns
    acronym-keep off entirely."""

    casing = SentenceCasing("uk", _member_of(set()))
    out = list(casing.apply(iter(["Це", "СБУ", "."])))
    assert ("СБУ", True) in out
    out = list(casing.apply(iter(["УВАГА", "НЕБЕЗПЕКА", "!"])))
    assert all(not keep for _surface, keep in out)


def test_probes_are_nfc_normalized() -> None:
    """apply() must NFC-normalize before the gate probe: an NFD token still
    matches its NFC dictionary key."""

    casing = SentenceCasing("de", _member_of({"schöne"}))  # NFC key
    out = list(casing.apply(iter([unicodedata.normalize("NFD", "Schöne")])))
    assert out[0] == ("schöne", False)


def test_buffer_cap_keeps_streaming() -> None:
    """Punctuation-free input must flush at the cap, not buffer until EOF:
    the first decision arrives after at most SENTENCE_BUFFER_CAP tokens."""

    consumed = 0

    def endless() -> Iterator[str]:
        nonlocal consumed
        while True:
            consumed += 1
            yield "Wort"

    casing = SentenceCasing("de", _member_of(set()))
    assert next(casing.apply(endless())) == ("Wort", False)
    assert consumed <= SENTENCE_BUFFER_CAP


def test_boundary_guard_suppresses_initials() -> None:
    """'J. Schmidt' is not a boundary; '1. Deze' is."""

    casing = SentenceCasing("nl", None)  # ungated: initial tokens lower
    surfaces = [s for s, _ in casing.apply(iter(["J", ".", "Schmidt", "kwam"]))]
    assert surfaces == ["j", ".", "Schmidt", "kwam"]
    surfaces = [s for s, _ in casing.apply(iter(["1", ".", "Deze", "zin"]))]
    assert surfaces == ["1", ".", "deze", "zin"]


def test_boundary_guard_buffered_path() -> None:
    """The buffered (acronym-language) path applies the same guard."""

    casing = SentenceCasing("lv", _member_of(set()))
    surfaces = [s for s, _ in casing.apply(iter(["Warte", "...", "Und"]))]
    assert surfaces == ["warte", "...", "und"]
    surfaces = [s for s, _ in casing.apply(iter(["H", ".", "L", ".", "Meier"]))]
    assert surfaces == ["h", ".", "L", ".", "Meier"]
