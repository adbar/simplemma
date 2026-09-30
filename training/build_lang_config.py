"""Per-language build-time tables consumed by dictionary_builder.py."""

import sys
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from simplemma.utils import (
    _ARABIC_MARKS,
    _APOSTROPHE_GLYPHS,
    normalize_token,
)

# All of Unicode, so no hardcoded block range misses a script.
_DECOMPOSABLE: list[tuple[int, frozenset[int]]] = [
    (cp, frozenset(map(ord, decomposed)))
    for cp in range(sys.maxunicode + 1)
    if len(decomposed := unicodedata.normalize("NFD", chr(cp))) >= 2
]


def _mark_fold_table(
    marks: frozenset[int],
    keep: str = "",
    scripts: tuple[str, ...] = ("LATIN ", "CYRILLIC "),
) -> dict[int, str | None]:
    """Table deleting `marks`, also from precomposed letters of `scripts`.

    `keep` lists letters whose mark is orthographic. `scripts` are Unicode
    name prefixes."""
    table: dict[int, str | None] = {cp: None for cp in marks}
    for cp, decomposed_ords in _DECOMPOSABLE:
        ch = chr(cp)
        if ch in keep or not marks & decomposed_ords:
            continue
        if not unicodedata.name(ch, "").startswith(scripts):
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        table[cp] = normalize_token(
            "".join(c for c in decomposed if ord(c) not in marks)
        )
    return table


# Arabic ي/ك to Persian ی/ک (lookalike glyphs).
_FA_NORMALIZE: dict[int, int | None] = {
    **_ARABIC_MARKS,
    ord("ي"): ord("ی"),
    ord("ك"): ord("ک"),
}

# Pitch and length marks, never typed in real text. Breve is not a BCS mark.
_HBS_PITCH_MARKS = frozenset(map(ord, "̀́̄̏̑̂"))
_HBS_PITCH_FOLD = _mark_fold_table(_HBS_PITCH_MARKS, keep="ćĆśŚźŹ")

# Acute only: grave ѝ is orthographic Bulgarian.
_BG_STRESS_FOLD = _mark_fold_table(frozenset({0x0301}), keep="ѓЃќЌ")

# Unlike bg, grave is only a stress mark in Ukrainian.
_UK_STRESS_FOLD = _mark_fold_table(frozenset({0x0300, 0x0301}), keep="ѓЃќЌ")

# U+0307 rides accented i, but ė is a real letter built from it.
_LT_PITCH_FOLD = _mark_fold_table(
    frozenset({0x0300, 0x0301, 0x0303, 0x0307}), keep="ėĖ"
)

# Pedagogical vowel length, never marked in real Latin text.
_LA_LENGTH_FOLD = _mark_fold_table(frozenset({0x0304, 0x0306}))

# The tokenizer yields the bare elided stem. ca/fr/it use the apostrophe strategy.
_ELISION_FOLD = str.maketrans("", "", "'" + _APOSTROPHE_GLYPHS + "᾽")

# Geresh/gershayim to the ASCII quotes UD gold uses.
_HE_QUOTE_FOLD = str.maketrans("״׳", "\"'")

# Cyrillic to Latin is 1:1, the reverse is ambiguous (lj/nj/dž).
_HBS_CYR_LETTERS = "абвгдђежзијклљмнњопрстћуфхцчџш"
_HBS_LAT_LETTERS = (
    "a b v g d đ e ž z i j k l lj m n nj o p r s t ć u f h c č dž š".split()
)
_HBS_CYR_TO_LAT: dict[int, str] = {
    **{ord(c): latin for c, latin in zip(_HBS_CYR_LETTERS, _HBS_LAT_LETTERS)},
    **{
        ord(c.upper()): latin.capitalize()
        for c, latin in zip(_HBS_CYR_LETTERS, _HBS_LAT_LETTERS)
    },
}


def _foreign_script_key(
    ks: frozenset[str], vs: frozenset[str], allowed: frozenset[str]
) -> bool:
    """Key uses no `allowed` script while the value does.

    Swap the arguments to test the value side instead."""
    return bool(ks) and bool(vs) and not (ks & allowed) and bool(vs & allowed)


def _foreign_script_entry(
    ks: frozenset[str], vs: frozenset[str], allowed: frozenset[str]
) -> bool:
    """Both sides scripted and the key uses no `allowed` script."""
    return bool(ks) and bool(vs) and not (ks & allowed)


# Module-level so lambdas don't rebuild them per entry.
_CYRILLIC_SCRIPTS = frozenset({"CYRILLIC"})
_GREEK_SCRIPTS = frozenset({"GREEK", "CYPRIOT", "LINEAR"})
_ARABIC_SCRIPTS = frozenset({"ARABIC"})
_DEVANAGARI_SCRIPTS = frozenset({"DEVANAGARI"})
_HEBREW_SCRIPTS = frozenset({"HEBREW"})
_LATIN_PLUS_CYRILLIC = frozenset({"LATIN", "CYRILLIC"})


def _ar_fa_junk(k: str, ks: frozenset[str], vs: frozenset[str]) -> bool:
    """Shared ar/fa predicate: same defect shape in both."""
    return _foreign_script_entry(ks, vs, _ARABIC_SCRIPTS)


# Per-language only: digit-leading and Latin keys are real words in many languages.
JUNK_ENTRY_PREDICATES: dict[
    str, Callable[[str, frozenset[str], frozenset[str]], bool]
] = {
    # uk digit-leading keys are paradigm-class codes ("10a").
    "uk": lambda k, ks, vs: (
        k[:1].isdigit()
        or _foreign_script_entry(ks, vs, _CYRILLIC_SCRIPTS)
        or _LATIN_PLUS_CYRILLIC <= ks
    ),
    "ar": _ar_fa_junk,
    # Swapped arguments catch English glosses as values.
    "grc": lambda k, ks, vs: (
        _foreign_script_entry(ks, vs, _GREEK_SCRIPTS)
        or _foreign_script_key(vs, ks, _GREEK_SCRIPTS)
    ),
    "fa": _ar_fa_junk,
    # Not the broad check: Latin abbreviations (US, DM) are legitimate in bg.
    "bg": lambda k, ks, vs: _foreign_script_key(ks, vs, _CYRILLIC_SCRIPTS),
    "hi": lambda k, ks, vs: _foreign_script_entry(ks, vs, _DEVANAGARI_SCRIPTS),
    # ms is biscriptal: Jawi keys are fine, a Latin key with a Jawi value is not.
    "ms": lambda k, ks, vs: _foreign_script_key(ks, vs, _ARABIC_SCRIPTS),
    "tl": lambda k, ks, vs: "TAGALOG" in ks,
    # Not the broad check: it would drop Phoenician attestations.
    "he": lambda k, ks, vs: _foreign_script_key(ks, vs, _HEBREW_SCRIPTS),
}


@dataclass(frozen=True)
class BuildNormalization:
    """A language's build-time-only normalization, applied in field order.

    key_alias adds a folded key twin, an existing exact key wins.
    value_fold rewrites values in place. value_script_fix transliterates a
    value whose script disagrees with its key. drop_folded_keys replaces
    the marked key instead of adding a twin, safe only when the marked
    spelling is never typed in real text."""

    key_alias: Mapping[int, int | str | None] | None = None
    value_fold: Mapping[int, int | str | None] | None = None
    value_script_fix: Mapping[int, str] | None = None
    drop_folded_keys: bool = False


BUILD_NORMALIZATION: dict[str, BuildNormalization] = {
    "ar": BuildNormalization(key_alias=str.maketrans("أإآٱى", "ااااي")),
    # Key alias only: a value fold would merge real pairs like все/всё.
    "ru": BuildNormalization(key_alias=str.maketrans("ёЁ", "еЕ")),
    # No drop_folded_keys: vocalized fa spellings do occur in real text.
    "fa": BuildNormalization(key_alias=_FA_NORMALIZE, value_fold=_FA_NORMALIZE),
    # value_script_fix: a Latin key must never carry a Cyrillic value.
    "hbs": BuildNormalization(
        key_alias=_HBS_PITCH_FOLD,
        value_fold=_HBS_PITCH_FOLD,
        value_script_fix=_HBS_CYR_TO_LAT,
        drop_folded_keys=True,
    ),
    "bg": BuildNormalization(
        key_alias=_BG_STRESS_FOLD, value_fold=_BG_STRESS_FOLD, drop_folded_keys=True
    ),
    "uk": BuildNormalization(
        key_alias=_UK_STRESS_FOLD, value_fold=_UK_STRESS_FOLD, drop_folded_keys=True
    ),
    "lt": BuildNormalization(
        key_alias=_LT_PITCH_FOLD, value_fold=_LT_PITCH_FOLD, drop_folded_keys=True
    ),
    # sl tonemic marks match BCS.
    "sl": BuildNormalization(
        key_alias=_HBS_PITCH_FOLD, value_fold=_HBS_PITCH_FOLD, drop_folded_keys=True
    ),
    "la": BuildNormalization(
        key_alias=_LA_LENGTH_FOLD, value_fold=_LA_LENGTH_FOLD, drop_folded_keys=True
    ),
    "grc": BuildNormalization(key_alias=_ELISION_FOLD),
    "el": BuildNormalization(key_alias=_ELISION_FOLD),
    "he": BuildNormalization(key_alias=_HE_QUOTE_FOLD, value_fold=_HE_QUOTE_FOLD),
}
