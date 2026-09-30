"""Casing decisions tested without dictionaries: membership is a set probe."""

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
from simplemma.lemmatizer import BETTER_LOWER


def _member_of(words: set[str]) -> MembershipCheck:
    return lambda token, _lang: token in words


def test_gated_langs_disjoint_from_fallback_lowering() -> None:
    """A language the fallback already lowercases must not also be gated."""

    assert GATED_INITIAL_LOWERING_LANGS.isdisjoint(BETTER_LOWER)


def test_sentence_boundary_detects_collapsed_runs() -> None:
    """Collapsed runs like '...' are boundaries, alnum-final tokens like '.270' not."""

    for term in [".", "?", "!", "…", "։", "...", "!!", "??", "?!"]:
        assert is_sentence_boundary(term), term
    for other in ["hello", "3.14", ".270", "l'homme", ""]:
        assert not is_sentence_boundary(other), other


def test_keepable_allcaps_excludes_long_roman_numerals() -> None:
    """Only numerals of 3 chars or more are excluded, 2-char acronyms stay keepable."""

    for acronym in ["CD", "DC", "MM", "MI", "MC", "XL", "XX", "USB", "SQL"]:
        assert is_keepable_allcaps(acronym), acronym
    for numeral in ["XII", "XIV", "MCM", "MIX", "MMXX"]:
        assert not is_keepable_allcaps(numeral), numeral


def test_streaming_path_keeps_legacy_boundary() -> None:
    """The streaming path must not reset after collapsed runs like '...'."""

    casing = SentenceCasing("fr", None)
    surfaces = [s for s, _keep in casing.apply(iter(["Fin", "...", "Alain"]))]
    assert surfaces == ["fin", "...", "Alain"]


def test_gated_initial_surface() -> None:
    """Members and all-caps forms are lowered, unknown capitalized words are kept."""

    casing = SentenceCasing("en", _member_of({"the"}))
    assert casing.initial_surface("The") == "the"
    assert casing.initial_surface("Iran") == "Iran"
    assert casing.initial_surface("NASA") == "nasa"


def test_acronym_keep_decisions() -> None:
    """Mid-sentence all-caps are kept, sentence-initial ones defer to the D' gate."""

    casing = SentenceCasing("de", _member_of({"mit"}))
    out = list(casing.apply(iter(["Die", "Firma", "MIT", "."])))
    assert ("MIT", True) in out
    out = list(casing.apply(iter(["MIT", "dem", "Auto", "."])))
    assert out[0] == ("mit", False)


def test_shouting_ratio_leave_one_out() -> None:
    """A lone acronym is kept, a mostly shouted sentence disables acronym-keep."""

    casing = SentenceCasing("uk", _member_of(set()))
    out = list(casing.apply(iter(["Це", "СБУ", "."])))
    assert ("СБУ", True) in out
    out = list(casing.apply(iter(["УВАГА", "НЕБЕЗПЕКА", "!"])))
    assert all(not keep for _surface, keep in out)


def test_probes_are_nfc_normalized() -> None:
    """An NFD token still matches its NFC dictionary key."""

    casing = SentenceCasing("de", _member_of({"schöne"}))
    out = list(casing.apply(iter([unicodedata.normalize("NFD", "Schöne")])))
    assert out[0] == ("schöne", False)


def test_buffer_cap_keeps_streaming() -> None:
    """Punctuation-free input flushes at the cap instead of buffering until EOF."""

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
    """'J. Schmidt' is not a boundary, '1. Deze' is."""

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
