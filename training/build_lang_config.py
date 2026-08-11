"""Per-language build-time configuration tables.

Normalization folds, script-based junk predicates, and transliteration
maps -- the "what's special about each language" half of the dictionary
build pipeline.  The pipeline logic that *consumes* these lives in
dictionary_builder.py.
"""

import sys
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from simplemma.utils import (
    _ARABIC_MARKS,
    _FOLDED_APOSTROPHES,
    _STRAIGHT_APOSTROPHE,
    normalize_token,
)

# ── mark-fold generator ─────────────────────────────────────────────


# All of Unicode, scanned once: no script's precomposed letters can be
# silently missed by a hardcoded block range.
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
    """Deletion of `marks` + every precomposed letter of `scripts` carrying
    one, generated from unicodedata (hand-typed tables shipped wrong twice).
    `keep` protects letters whose mark is orthographic, not pitch/length
    marking (hbs/sl ć). `scripts` are Unicode-name prefixes: a fold names its
    scripts, so a bg acute fold never touches Greek accented letters."""
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


# ── per-language fold tables ─────────────────────────────────────────

# fa tashkeel/tatweel deletion (was 23.8% of keys) + Arabic-script ي/ك ->
# standard Persian ی/ک (was 41% of keys, 23% of values).
_FA_NORMALIZE: dict[int, int | None] = {
    **_ARABIC_MARKS,
    ord("ي"): ord("ی"),
    ord("ك"): ord("ک"),
}

# hbs pitch (grave/acute) + length (macron/double-grave/inverted-breve, rare
# circumflex) marking: a Wiktionary headword convention on 13.3% of shipped
# keys, never typed in real text (0 marked tokens in 297k UD gold). NOT
# breve U+0306 (2 foreign-loan keys, not a BCS convention). keep=: ć/ś/ź are
# real letters (c/s/z-acute), not pitch marks.
_HBS_PITCH_MARKS = frozenset(map(ord, "̀́̄̏̑̂"))
_HBS_PITCH_FOLD = _mark_fold_table(_HBS_PITCH_MARKS, keep="ćĆśŚźŹ")

# bg stress = combining acute only -- grave stays: ѝ (i-grave, "her") and its
# family are ORTHOGRAPHIC Bulgarian, not stress marking (unlike uk below).
# keep=: ѓ/ќ are Macedonian letters (acute-based), guarded though 0 in dict.
_BG_STRESS_FOLD = _mark_fold_table(frozenset({0x0301}), keep="ѓЃќЌ")

# uk stress = acute + rare grave; neither is orthographic in Ukrainian (no
# real ѐ/ѝ-style letters in the shipped dict -- verified, not assumed).
# keep=: ѓ/ќ guarded like bg (0 in dict). NOT ѐ/ѝ: real pitch-fold targets.
_UK_STRESS_FOLD = _mark_fold_table(frozenset({0x0300, 0x0301}), keep="ѓЃќЌ")

# lt pitch accent: grave/acute/tilde marking + a redundant dotted-i encoding
# (U+0307) that rides accented i. ė/Ė are real Lithuanian letters (also
# built from e+U+0307) and must be kept.
_LT_PITCH_FOLD = _mark_fold_table(
    frozenset({0x0300, 0x0301, 0x0303, 0x0307}), keep="ėĖ"
)

# la pedagogical vowel length (the grc precedent, applied build-side instead
# of as a runtime canon fold since real Latin text never marks length).
_LA_LENGTH_FOLD = _mark_fold_table(frozenset({0x0304, 0x0306}))

# grc/el elision: strip so the tokenizer's bare stem aliases to the value.
# Not ca/fr/it, where the elided form is a single letter (apostrophe_boundary
# handles those instead).
_ELISION_FOLD = str.maketrans(
    "", "", "".join((_STRAIGHT_APOSTROPHE, *_FOLDED_APOSTROPHES, "᾽"))
)

# he geresh/gershayim -> the ASCII quotes real text and UD gold use
_HE_QUOTE_FOLD = str.maketrans("״׳", "\"'")

# Serbian Cyrillic -> Latin is 1:1 per letter (the reverse is not: lj/nj/dž
# digraphs are ambiguous), so this direction is deterministically safe.
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


# ── script-based junk predicates ─────────────────────────────────────


def _foreign_script_key(
    ks: frozenset[str], vs: frozenset[str], allowed: frozenset[str]
) -> bool:
    """Key uses NO script in `allowed` while the value uses one -- a
    transliteration/IPA row leaked in as a word form (grc Beta-code
    "hubrisin" -> "ὑβρίς"). Mixed-script keys never flag; swap the arguments
    for the value direction (gloss-as-lemma, grc κάλαμος -> "plants").
    `ks`/`vs` are _script_classes, computed once in _drop_junk_keys."""
    return bool(ks) and bool(vs) and not (ks & allowed) and bool(vs & allowed)


def _foreign_script_entry(
    ks: frozenset[str], vs: frozenset[str], allowed: frozenset[str]
) -> bool:
    """Broader: both sides scripted, key has no script in `allowed` --
    the union of _foreign_script_key with the wholly-foreign shape
    (planted selfmaps like grc "plants" -> "plants")."""
    return bool(ks) and bool(vs) and not (ks & allowed)


# Script sets the predicates test against, hoisted to module level: a
# lambda-local frozenset would be rebuilt per entry across 600k+ rows.
_CYRILLIC_SCRIPTS = frozenset({"CYRILLIC"})
_GREEK_SCRIPTS = frozenset({"GREEK", "CYPRIOT", "LINEAR"})
_ARABIC_SCRIPTS = frozenset({"ARABIC"})
_DEVANAGARI_SCRIPTS = frozenset({"DEVANAGARI"})
_HEBREW_SCRIPTS = frozenset({"HEBREW"})
_LATIN_PLUS_CYRILLIC = frozenset({"LATIN", "CYRILLIC"})


def _ar_fa_junk(k: str, ks: frozenset[str], vs: frozenset[str]) -> bool:
    """Shared ar/fa predicate: same defect shape in both."""
    return _foreign_script_entry(ks, vs, _ARABIC_SCRIPTS)


# Per-language (key, key_scripts, value_scripts) -> drop predicates. Each
# entry is a verified, language-specific defect -- there is no universal
# "foreign script" or "digit-leading" rule (a digit-leading token is a real
# word in many languages: da "0-1-nederlaget", de "1-Cent-Münze", en
# "1000000", ga "1000ú", hu "10-es", sv "10-krona", all verified present in
# their shipped dicts; a Latin-script key is legitimate in most languages
# too).
JUNK_ENTRY_PREDICATES: dict[
    str, Callable[[str, frozenset[str], frozenset[str]], bool]
] = {
    # uk: digit-leading paradigm-class codes ("10a") -- all verified junk;
    # BGN transliteration rows ("zanos" -> "занос") and wholly-foreign
    # romanized identity rows ("vony", 11 shipped), both via the broad
    # entry check; every Latin+Cyrillic mixed key (homoglyph poisoning,
    # 15,828 fill entries -- broader than the evidence, IT-фахівець would
    # drop too).
    "uk": lambda k, ks, vs: (
        k[:1].isdigit()
        or _foreign_script_entry(ks, vs, _CYRILLIC_SCRIPTS)
        or _LATIN_PLUS_CYRILLIC <= ks
    ),
    # ar: IPA transcription rows (98,864 shipped entries) + wholly-foreign
    # English junk and Judeo-Arabic spellings (95, polluted langdetect vs he).
    "ar": _ar_fa_junk,
    # grc: Beta-code romanization keys and the selfmaps they seed
    # (CYPRIOT/LINEAR stay allowed, genuine early-Greek attestations); the
    # swapped-argument direction catches English glosses (κάλαμος -> "plants").
    "grc": lambda k, ks, vs: (
        _foreign_script_entry(ks, vs, _GREEK_SCRIPTS)
        or _foreign_script_key(vs, ks, _GREEK_SCRIPTS)
    ),
    # fa: romanized rows ("and" -> بودن), template artifacts, English junk
    # -- 4,938 shipped entries (9.4%, 2026-08).
    "fa": _ar_fa_junk,
    # bg: BGN transliteration rows ("rádost" -> "радост"). The broad entry
    # check NOT used: its extra hits are US/DM abbreviations, legitimate in
    # bg text.
    "bg": lambda k, ks, vs: _foreign_script_key(ks, vs, _CYRILLIC_SCRIPTS),
    # hi: Urdu-script rows from the shared Hindi/Urdu extraction -- real
    # Hindi text is Devanagari. PLUS wholly-foreign ("sweets").
    "hi": lambda k, ks, vs: _foreign_script_entry(ks, vs, _DEVANAGARI_SCRIPTS),
    # ms: biscriptal, Jawi keys KEPT (3,301 shipped); a Latin key must never
    # resolve to a Jawi value (446 did).
    "ms": lambda k, ks, vs: _foreign_script_key(ks, vs, _ARABIC_SCRIPTS),
    # tl: Baybayin keys via alt_of, no modern running-text use (3,909
    # shipped). Key-side check: 5 entries carry Baybayin VALUES too.
    "tl": lambda k, ks, vs: "TAGALOG" in ks,
    # he: Latin keys -> Hebrew values (transliterations). The broad entry
    # check NOT used: its extra hits are Phoenician attestations, kept like
    # grc's ancient scripts.
    "he": lambda k, ks, vs: _foreign_script_key(ks, vs, _HEBREW_SCRIPTS),
}


# ── BuildNormalization + registry ────────────────────────────────────


@dataclass(frozen=True)
class BuildNormalization:
    """A language's build-time-only normalization (unlike canonicalize_token's
    symmetric fold in simplemma.utils, applied equally to build-time keys and
    runtime queries). key_alias adds a folded key twin, value unchanged, an
    existing exact key always wins. value_fold rewrites values in place, keys
    untouched, so it can never create a collision. value_script_fix
    transliterates a value whose script disagrees with its (unmarked) key --
    only ever narrows a value's script, never touches keys. A language
    needing both value_fold and key_alias for the same fold (e.g. fa)
    references ONE table object in both fields, so the mechanisms cannot
    drift apart on what "normalization" means -- as two hand-synced copies
    once did. Applied in this field order by `_apply_build_normalization`.

    drop_folded_keys additionally REPLACES a folded key instead of adding a
    twin: safe only when the UNFOLDED spelling is never typed in real text
    (verified per language, e.g. fa vocalization, hbs/bg/uk/lt/sl/la
    pitch/stress/length marks) -- NOT for a language where both spellings
    are genuinely attested (ar hamza-seat variance, ru's real ё usage), or
    the real spelling becomes unreachable. Cuts shipped size 16-49% (marked
    keys front-code poorly against their plain twin -- a mid-word combining
    mark breaks the shared byte prefix)."""

    key_alias: Mapping[int, int | str | None] | None = None
    value_fold: Mapping[int, int | str | None] | None = None
    value_script_fix: Mapping[int, str] | None = None
    drop_folded_keys: bool = False


BUILD_NORMALIZATION: dict[str, BuildNormalization] = {
    # ar hamza-seat/maqsura spelling variance. +0.8-1.2pp ar.
    "ar": BuildNormalization(key_alias=str.maketrans("أإآٱى", "ااااي")),
    # ru text routinely writes е for ё while lemmas keep ё (SynTagRus gold:
    # 85 ё-forms vs 234 ё-lemmas) -- the alias bridges е-spelled input to the
    # ё-spelled entry. Key alias ONLY: a symmetric or value fold would merge
    # real pairs (все/всё) and treebanks contradict each other on lemma
    # spelling (GSD gold is е-spelled, SynTagRus ё-spelled). Positive on all
    # 5 UD treebanks, up to +0.8pp type (poetry).
    "ru": BuildNormalization(key_alias=str.maketrans("ёЁ", "еЕ")),
    # queries never need folding here -- real Persian text is never
    # vocalized or Arabic-spelled, and a query-side fold (a _CANON_TABLES
    # entry) risks merging distinct keys for zero measured benefit.
    # drop_folded_keys NOT set, unlike the mark-fold langs below: the
    # assumption that fa's vocalized spelling is NEVER typed does NOT hold --
    # measured drop-gate FAIL on fa_perdt (token -0.0012, type -0.0002), so
    # some real fa text does exercise the vocalized key directly. Keep both.
    "fa": BuildNormalization(key_alias=_FA_NORMALIZE, value_fold=_FA_NORMALIZE),
    # dictionary-only marks (fa-shaped: build-side fold suffices, 26.4k of
    # 89.9k marked keys had no plain twin at all) + hbs is dual-script but a
    # LATIN key must never carry a CYRILLIC value (738 shipped entries did,
    # e.g. Milorad -> Милорад -- wrong for any monoscript text).
    # drop_folded_keys: the marked spelling is never typed in real text (0
    # marked tokens in 297k UD gold) -- safe to replace, not alias (~49% smaller).
    "hbs": BuildNormalization(
        key_alias=_HBS_PITCH_FOLD,
        value_fold=_HBS_PITCH_FOLD,
        value_script_fix=_HBS_CYR_TO_LAT,
        drop_folded_keys=True,
    ),
    # same shape as hbs, dictionary-only marks: bg 55.6% of keys stress-
    # marked, uk 26.4%, lt 7.4%, sl tonemic (hbs's own table), la 13.3%
    # pedagogical length -- none typed in real text, all measured gate-PASS
    # on every available treebank (12/12) before shipping. drop_folded_keys
    # for the same reason as fa/hbs above: cuts shipped size 16-35%.
    "bg": BuildNormalization(
        key_alias=_BG_STRESS_FOLD, value_fold=_BG_STRESS_FOLD, drop_folded_keys=True
    ),
    "uk": BuildNormalization(
        key_alias=_UK_STRESS_FOLD, value_fold=_UK_STRESS_FOLD, drop_folded_keys=True
    ),
    "lt": BuildNormalization(
        key_alias=_LT_PITCH_FOLD, value_fold=_LT_PITCH_FOLD, drop_folded_keys=True
    ),
    # sl tonemic marking uses the identical mark set and ć-trap as BCS
    "sl": BuildNormalization(
        key_alias=_HBS_PITCH_FOLD, value_fold=_HBS_PITCH_FOLD, drop_folded_keys=True
    ),
    "la": BuildNormalization(
        key_alias=_LA_LENGTH_FOLD, value_fold=_LA_LENGTH_FOLD, drop_folded_keys=True
    ),
    # elided headwords (Δί', ἀλλ'): the tokenizer yields the bare stem
    "grc": BuildNormalization(key_alias=_ELISION_FOLD),
    "el": BuildNormalization(key_alias=_ELISION_FOLD),
    # he acronyms are spelled with geresh/gershayim or ASCII quotes; fold both
    "he": BuildNormalization(key_alias=_HE_QUOTE_FOLD, value_fold=_HE_QUOTE_FOLD),
}
