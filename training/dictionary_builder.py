"""Build a language's runtime lemmatization dictionary (a form->lemma map).

Pipeline: base -> _apply_layers (fill, override) -> _scrub ->
_apply_build_normalization -> _ensure_value_selfmaps -> _drop_junk_keys ->
frontcode. Plain str dicts throughout; bytes only at the two edges.

Base: the installed dictionary itself (pinned artifact, routine rebuilds
idempotent). A wordlist directory (`listpath`) ingests new data instead:
resolved list as base (duplicate lines = evidence); an already-shipped
language's installed mappings win shared keys, so a list only ADDS.

Key invariants: _valid_key (universal post-layer guard) vs _reachable_key
(stricter, machine sources only; overrides exempt for deliberate elisions
like ro "de-").
"""

import argparse
import logging
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.tokenizer import simple_tokenizer
from simplemma.strategies.dictionaries import dictionary_factory, frontcode
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    _load_dictionary_from_disk,
)
from simplemma.utils import (
    _ARABIC_MARKS,  # private, but this is the reviewed ar/fa tashkeel table
    _FOLDED_APOSTROPHES,  # private: utils owns the apostrophe glyph set
    _STRAIGHT_APOSTROPHE,
    canonicalize_token,
    levenshtein_dist,
    normalize_token,
)
from training.clean_wordlist import canonicalize, check_field, read_pairs

# sw inflection is prefixal (forms share an ending, not a start), so
# front-coding uses reversed-byte keys here.
FRONTCODE_REVERSE_KEY_LANGS = {"sw"}

# Per-language source layers merged by _apply_layers (precedence: overrides >
# base > fill; see _compose_dictionary for what the base is).
OVERRIDES_DIR = Path(__file__).parent / "overrides"
FILL_DIR = Path(__file__).parent / "fill"

# Wikidata fill allowlist (gated by assess_wikidata_fill.py; fill/ is
# gitignored, so a stale local TSV must fail loud). Gate-rejected:
# fr/it/tr/id/fa/se; nb has no UD treebank.
V2_FILL_LANGS = frozenset(
    {
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "fi",
        "la",
        "nb",
        "nl",
        "nn",
        "pl",
        "pt",
        "ru",
        "sk",
        "sv",
        "uk",
    }
)

LOGGER = logging.getLogger(__name__)

# Punctuation a tokenizer never yields inside one token: comma/colon/star/
# slash/plus/underscore anywhere, or a leading/trailing hyphen (affix
# fragment). Hebrew maqaf (U+05BE) is Wiktionary's hyphen for bound-morpheme
# headwords (ב־), so it counts as a hyphen here.
FIELD_PUNCT = re.compile(r"[,:*/\+_]|.+[-־]$|^[-־].+")


def _is_single_token(text: str) -> bool:
    """True if a tokenizer could yield `text` as ONE token: no space and no
    FIELD_PUNCT. The orthogonal 'not mojibake/control' check is check_field;
    the two callers (_collect_candidates on raw columns, _reachable_key via
    _valid_key) each pair this with it."""
    return " " not in text and not FIELD_PUNCT.search(text)


def _collect_candidates(
    path: Path, langcode: str
) -> tuple[dict[str, Counter[str]], set[str]]:
    """First pass: filter input lines, counting each (form, lemma) pair as evidence.

    Per-line diagnostics (wrong format, rule mismatch) are DEBUG-gated: the
    rule check is otherwise skipped for cost."""
    diagnose = LOGGER.isEnabledFor(logging.DEBUG)
    candidates: defaultdict[str, Counter[str]] = defaultdict(Counter)
    lemmas: set[str] = set()
    with open(path, encoding="utf-8") as filehandle:
        for line in filehandle:
            # NFC + per-language canon here: runtime lookups apply both, so
            # keys must match (canonicalize_token is a no-op outside its
            # registered languages, see _CANON_TABLES in simplemma.utils).
            # NFC AGAIN after canon: the translate can strand a stacked
            # combining mark (la 'Boō̈tēs': ō->o leaves an NFC-invalid key).
            columns = [
                normalize_token(canonicalize_token(normalize_token(c), langcode))
                for c in line.strip().split("\t")
            ]
            if len(columns) != 2 or not columns[0]:
                LOGGER.debug("wrong format: %s", line.strip())
                continue
            # drop fields a tokenizer could never yield as one token, or
            # carrying mojibake/control chars.
            if any(not _is_single_token(c) or check_field(c) for c in columns):
                continue
            if len(columns[0]) == 1 and len(columns[1]) > 6:
                continue
            if len(columns[0]) > 6 and len(columns[1]) == 1:
                continue
            # diagnose rules disagreeing with the list
            if diagnose and len(columns[1]) > 6 and langcode in RULE_FUNCTIONS:
                rule = RULE_FUNCTIONS[langcode](columns[1])
                if rule and rule != columns[0]:
                    LOGGER.debug(
                        "rule mismatch: %s %s %s", columns[1], columns[0], rule
                    )
            candidates[columns[1]][columns[0]] += 1
            lemmas.add(columns[0])
    return candidates, lemmas


# Headword identity must NOT override an attested form-of mapping here (grc
# ἀκούσας; removal measured -3.8/-7.8pp). Force-identity stays the default,
# gate-proven net-positive elsewhere (nl +17pp, bg/uk +6pp).
IDENTITY_SOFT_LANGS = frozenset({"grc"})


# Break an attestation TIE by paradigm size before Levenshtein: distance
# alone lets a rare lexeme win an ultra-frequent form (grc ἦν). Per-language,
# gated; gl/lt FAILED and the prior loses elsewhere -- never the default.
PARADIGM_PRIOR_LANGS: frozenset[str] = frozenset(
    {"cy", "el", "et", "grc", "hy", "nl", "sk", "sv"}
)


def _resolve_candidates(
    candidates: dict[str, Counter[str]],
    lemmas: set[str],
    langcode: str,
) -> dict[str, str]:
    """Second pass: pick one lemma per form (most attestations, then paradigm
    size for PARADIGM_PRIOR_LANGS, then distance)."""
    diagnose = LOGGER.isEnabledFor(logging.DEBUG)
    paradigm_size: Counter[str] = Counter()
    if langcode in PARADIGM_PRIOR_LANGS:
        for counts in candidates.values():
            paradigm_size.update(counts.keys())
    mydict: dict[str, str] = {}
    for word_form, counts in candidates.items():
        options = dict(counts)
        if word_form in lemmas:
            options.setdefault(word_form, 0)
        if len(options) == 1:
            mydict[word_form] = next(iter(options))
            continue
        best = min(
            options.items(),
            key=lambda item: (
                -item[1],
                -paradigm_size[item[0]],
                levenshtein_dist(word_form, item[0]),
                item[0],
            ),
        )[0]
        if diagnose:
            LOGGER.debug(
                "diverging: %s -> %s | candidates: %s",
                word_form,
                best,
                sorted(options.items()),
            )
        mydict[word_form] = best
    # Force identity: a headword is its own lemma. Soft (setdefault only) for
    # IDENTITY_SOFT_LANGS and for lemmas attested only by their own line
    # (forcing those measured -1.3..-2.6pp).
    soft = langcode in IDENTITY_SOFT_LANGS
    strong = {
        lemma
        for form, counts in candidates.items()
        for lemma in counts
        if lemma != form
    }
    for word in lemmas:
        if word in strong and not soft:
            mydict[word] = word
        else:
            mydict.setdefault(word, word)
    return mydict


def _read_dict(path: Path, langcode: str) -> dict[str, str]:
    """Resolve a raw ``lemma<TAB>form`` wordlist at `path` into a form->lemma dict."""
    candidates, lemmas = _collect_candidates(path, langcode)
    mydict = _resolve_candidates(candidates, lemmas, langcode)
    LOGGER.debug("%s: %d entries", langcode, len(mydict))
    return mydict


def _layer_entries(
    path: Path, langcode: str, *, skip_level: int = logging.INFO
) -> dict[str, str]:
    """A curated lemma<TAB>form layer file as a form->lemma mapping,
    canonicalized like the base wordlist (_collect_candidates) so a
    reviewed file can't ship an unreachable dead key.

    read_pairs enforces key hygiene and fails loud on corruption. Skipping a
    spaced field is policy, not corruption: a multi-word form (e.g. Wikidata
    'top hat') is unreachable -- the tokenizer never yields it as a single
    token -- and a multi-word lemma (UD 'c.q.' -> 'casu quo') must not ship
    as lemmatizer output."""
    pairs = read_pairs(path)
    spaceless = {
        form: lemma
        for form, lemma in pairs.items()
        if " " not in form and " " not in lemma
    }
    if len(spaceless) < len(pairs):
        # skip_level: routine in machine fill (DEBUG), a finding in overrides (INFO)
        LOGGER.log(
            skip_level,
            "%s: skipped %d entries with a spaced form or lemma",
            path.name,
            len(pairs) - len(spaceless),
        )
    entries: dict[str, str] = {}
    for form, lemma in spaceless.items():
        # NFC after canon (see _collect_candidates): a stranded combining
        # mark would die in _scrub.
        cform = normalize_token(canonicalize_token(form, langcode))
        clemma = normalize_token(canonicalize_token(lemma, langcode))
        if cform in entries and entries[cform] != clemma:
            raise ValueError(
                f"{path}: two entries fold to the same canonical form "
                f"{cform!r} with different lemmas ({entries[cform]!r} vs "
                f"{clemma!r}) -- reviewed entries must agree once folded "
                f"to the runtime key space"
            )
        entries[cform] = clemma
    return entries


def _apply_layers(
    base: dict[str, str], langcode: str, overrides_dir: Path | None = None
) -> dict[str, str]:
    """Merge the optional per-language source layers into the base dict.
    Precedence: overrides > base > fill; fill never displaces a base entry.
    `overrides_dir` overrides OVERRIDES_DIR (candidate gating, tests)."""
    merged = dict(base)
    fill_path = FILL_DIR / f"{langcode}.tsv"
    if fill_path.exists():
        if langcode not in V2_FILL_LANGS:
            raise ValueError(
                f"{fill_path}: fill present for {langcode!r}, which is not in "
                f"V2_FILL_LANGS (the reviewed ship decision) -- delete the stale "
                f"file or gate the language and add it to the allowlist"
            )
        # fill is machine-extracted, so unlike overrides it gets the base's
        # aggressive key hygiene (e.g. suffix lexemes like "-al" are unreachable).
        fill_entries = _layer_entries(fill_path, langcode, skip_level=logging.DEBUG)
        for form, lemma in _clean_base(fill_entries).items():
            merged.setdefault(form, lemma)
        LOGGER.info("%s: fill layer applied -> %s entries", langcode, len(merged))
    override_path = (overrides_dir or OVERRIDES_DIR) / f"{langcode}.tsv"
    if override_path.exists():
        merged.update(_layer_entries(override_path, langcode))
        LOGGER.info("%s: override layer applied -> %s entries", langcode, len(merged))
    return merged


# Wiktionary template placeholders that leaked into old dicts as "lemmas".
_PLACEHOLDER_VALUES = {"prpers"}


def _valid_key(key: str) -> bool:
    """Universal key invariant, checked post-layer: NFC (normalize_token, the
    exact canonicalization runtime queries get) and free of control/mojibake
    chars. Deliberately NOT clean_wordlist.canonicalize: that also folds curly
    quotes, which runtime lookups keep, so folding here would silently drop
    reachable keys (e.g. an apostrophe form like uk "м’ясо") and reviewed
    override forms."""
    return normalize_token(key) == key and not check_field(key)


def _reachable_key(key: str) -> bool:
    """Stricter invariant for MACHINE sources (base wordlist, Wikidata fill):
    additionally no space or punctuation a tokenizer never yields as one token.
    Reviewed overrides are exempt -- they carry deliberate elisions (ro "de-")."""
    return _valid_key(key) and _is_single_token(key)


def _clean_base(base: dict[str, str]) -> dict[str, str]:
    """Drop unreachable keys from a machine source used as a base or layer.
    Pre-layer ONLY: overrides are re-applied afterwards, so they're untouched."""
    out = {k: v for k, v in base.items() if _reachable_key(k)}
    if len(out) < len(base):
        LOGGER.info("clean_base: dropped %d unreachable keys", len(base) - len(out))
    return out


def _junk_entry(key: str, value: str) -> bool:
    """A non-identity entry whose value is an affix fragment (Wiktionary
    junk, e.g. schaft -> -schaft) or carries no letters, or whose key has
    none (mined UD noise, e.g. bg ":" -> "на"). Identity entries stay, and
    the check is deliberately narrow -- commas/underscores appear in legit
    compound lemmas."""
    if value == key:
        return False
    return (
        value.startswith(("-", "־"))  # ASCII hyphen or Hebrew maqaf
        or value.endswith(("-", "־"))
        or not any(ch.isalpha() for ch in value)
        or not any(ch.isalpha() for ch in key)
    )


def _scrub(mydict: dict[str, str]) -> dict[str, str]:
    """Final post-layer pass: drops keys failing _valid_key (not the stricter
    _reachable_key, since override elisions must survive) and drops values
    that are junk/placeholder after canonicalize. Values, unlike keys, go
    through canonicalize (straight apostrophe) even when the key keeps a
    curly one -- harmless, since the runtime's apostrophe-variant fallback
    bridges the two glyphs."""
    out: dict[str, str] = {}
    dropped_key = fixed_val = dropped_val = 0
    for k, v in mydict.items():
        if not _valid_key(k):
            dropped_key += 1
            continue
        nv, _ = canonicalize(v)
        # " " in nv: a multi-word lemma must never ship as lemmatizer output
        if (
            not nv
            or " " in nv
            or check_field(nv)
            or nv in _PLACEHOLDER_VALUES
            or _junk_entry(k, nv)
        ):
            dropped_val += 1
            continue
        fixed_val += nv != v
        out[k] = nv
    if dropped_key or dropped_val or fixed_val:
        LOGGER.info(
            "scrub: dropped %d junk keys, dropped %d junk values, fixed %d values",
            dropped_key,
            dropped_val,
            fixed_val,
        )
    return out


@lru_cache(maxsize=None)
def _char_script(ch: str) -> str | None:
    """Script name of one alphabetic char, else None. Cached: uncached,
    unicodedata.name dominated the junk stage (5-8s per large build)."""
    if not ch.isalpha():
        return None
    try:
        return unicodedata.name(ch).split()[0]
    except ValueError:
        return None


def _script_classes(word: str) -> frozenset[str]:
    """Every Unicode script name (the part of unicodedata.name before its
    first space, e.g. "CYRILLIC" from "CYRILLIC SMALL LETTER A") among
    `word`'s alphabetic characters. Empty for a non-alphabetic string
    (digits, punctuation) -- callers must not treat that as "foreign"."""
    return frozenset(s for s in map(_char_script, word) if s is not None)


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

# Per-language (key, key_scripts, value_scripts) -> drop predicates. Each
# entry is a verified, language-specific defect -- there is no universal
# "foreign script" or "digit-leading" rule (a digit-leading token is a real
# word in many languages: da "0-1-nederlaget", de "1-Cent-Münze", en
# "1000000", ga "1000ú", hu "10-es", sv "10-krona", all verified present in
# their shipped dicts; a Latin-script key is legitimate in most languages
# too).
_JUNK_ENTRY_PREDICATES: dict[
    str, Callable[[str, frozenset[str], frozenset[str]], bool]
] = {
    # uk: digit-leading paradigm-class codes ("10a") -- all verified junk;
    # BGN transliteration rows ("zanos" -> "занос") and wholly-foreign
    # romanized identity rows ("vony", 11 shipped), both via the broad
    # entry check; every Latin+Cyrillic mixed key (homoglyph poisoning,
    # 15,828 fill entries -- broader than the evidence, IT-фахівець would
    # drop too).
    "uk": lambda k, ks, vs: (
        bool(re.match(r"^[\d¹²³]", k))
        or _foreign_script_entry(ks, vs, _CYRILLIC_SCRIPTS)
        or _LATIN_PLUS_CYRILLIC <= ks
    ),
    # ar: IPA transcription rows (98,864 shipped entries) + wholly-foreign
    # English junk and Judeo-Arabic spellings (95, polluted langdetect vs he).
    "ar": lambda k, ks, vs: _foreign_script_entry(ks, vs, _ARABIC_SCRIPTS),
    # grc: Beta-code romanization keys and the selfmaps they seed
    # (CYPRIOT/LINEAR stay allowed, genuine early-Greek attestations); the
    # swapped-argument direction catches English glosses (κάλαμος -> "plants").
    "grc": lambda k, ks, vs: (
        _foreign_script_entry(ks, vs, _GREEK_SCRIPTS)
        or _foreign_script_key(vs, ks, _GREEK_SCRIPTS)
    ),
    # fa: romanized rows ("and" -> بودن), template artifacts, English junk
    # -- 4,938 shipped entries (9.4%, 2026-08).
    "fa": lambda k, ks, vs: _foreign_script_entry(ks, vs, _ARABIC_SCRIPTS),
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


def _drop_junk_keys(mydict: dict[str, str], langcode: str) -> dict[str, str]:
    """Drop entries matching langcode's _JUNK_ENTRY_PREDICATES entry; a
    no-op for any other language. Each side's script set is computed once
    here and handed to the predicate."""
    predicate = _JUNK_ENTRY_PREDICATES.get(langcode)
    if predicate is None:
        return mydict
    out = {
        k: v
        for k, v in mydict.items()
        if not predicate(k, _script_classes(k), _script_classes(v))
    }
    if len(out) < len(mydict):
        LOGGER.info(
            "%s: junk filter dropped %d entries", langcode, len(mydict) - len(out)
        )
    return out


# fa tashkeel/tatweel deletion (was 23.8% of keys) + Arabic-script ي/ك ->
# standard Persian ی/ک (was 41% of keys, 23% of values).
_FA_NORMALIZE: dict[int, int | None] = {
    **_ARABIC_MARKS,
    ord("ي"): ord("ی"),
    ord("ك"): ord("ک"),
}


def _mark_fold_table(marks: frozenset[int], keep: str = "") -> dict[int, str | None]:
    """Deletion of `marks` + every precomposed Latin/Cyrillic letter carrying
    one, generated from unicodedata (hand-typed tables shipped wrong twice).
    `keep` protects letters whose mark is orthographic, not pitch/length
    marking (hbs/sl ć)."""
    table: dict[int, str | None] = {cp: None for cp in marks}
    for cp in (*range(0x00C0, 0x0250), *range(0x0400, 0x0500), *range(0x1E00, 0x1F00)):
        ch = chr(cp)
        if ch in keep:
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        if len(decomposed) < 2 or not marks & set(map(ord, decomposed)):
            continue
        table[cp] = unicodedata.normalize(
            "NFC", "".join(c for c in decomposed if ord(c) not in marks)
        )
    return table


# hbs pitch (grave/acute) + length (macron/double-grave/inverted-breve, rare
# circumflex) marking: a Wiktionary headword convention on 13.3% of shipped
# keys, never typed in real text (0 marked tokens in 297k UD gold). NOT
# breve U+0306 (2 foreign-loan keys, not a BCS convention). keep=: ć/ś/ź are
# real letters (c/s/z-acute), not pitch marks.
_HBS_PITCH_MARKS = frozenset(map(ord, "̀́̄̏̑̂"))
_HBS_PITCH_FOLD = _mark_fold_table(_HBS_PITCH_MARKS, keep="ćĆśŚźŹ")

# sl tonemic marking uses the identical mark set and the identical ć-trap
# (BCS proper nouns in sl text carry ć): reuse the table object, not a copy.
_SL_TONEME_FOLD = _HBS_PITCH_FOLD

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
_ELISION_GLYPHS = (_STRAIGHT_APOSTROPHE, *_FOLDED_APOSTROPHES, "᾽")
_ELISION_FOLD = str.maketrans("", "", "".join(_ELISION_GLYPHS))

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
    "sl": BuildNormalization(
        key_alias=_SL_TONEME_FOLD, value_fold=_SL_TONEME_FOLD, drop_folded_keys=True
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


def _fold_values(
    mydict: dict[str, str], table: Mapping[int, int | str | None]
) -> dict[str, str]:
    """Rewrite each entry's VALUE per `table`. Keys are untouched, so this can
    never create a collision -- unlike a symmetric fold or a key alias.
    NFC after translate: folding a stacked diacritic strands its mark."""
    return {k: normalize_token(v.translate(table)) for k, v in mydict.items()}


_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def _fix_value_scripts(
    mydict: dict[str, str], table: Mapping[int, str]
) -> dict[str, str]:
    """Transliterate a Cyrillic VALUE on a Cyrillic-free key per `table`. A
    value still carrying Cyrillic after transliteration (letters outside the
    table's alphabet, i.e. a foreign word) is left unchanged rather than
    half-transliterated; mixed-script keys are never touched."""
    out = dict(mydict)
    for key, value in mydict.items():
        if _CYRILLIC.search(value) and not _CYRILLIC.search(key):
            new_value = value.translate(table)
            if not _CYRILLIC.search(new_value):
                out[key] = new_value
    return out


def _add_key_aliases(
    mydict: dict[str, str],
    table: Mapping[int, int | str | None],
    *,
    drop_original: bool = False,
) -> dict[str, str]:
    """Add each entry's folded-key alias per `table`, value unchanged. An
    existing exact key is never overwritten by an alias or a replacement.
    `drop_original` REPLACES the folded key instead of keeping both (see
    BuildNormalization.drop_folded_keys) -- only ever set by a caller that
    has verified the unfolded spelling is never queried."""
    out = dict(mydict)
    for key, value in mydict.items():
        # NFC after translate: this runs post-_scrub, so a stranded combining
        # mark (la 'Boō̈tēs': ō->o + diaeresis) would ship NFC-invalid.
        alias = normalize_token(key.translate(table))
        # a mark-only key folds to "" (survives _scrub via the identity
        # exemption in _junk_entry) -- never plant an empty key
        if alias and alias != key:
            out.setdefault(alias, value)
            if drop_original:
                del out[key]
    return out


def _ensure_value_selfmaps(mydict: dict[str, str]) -> dict[str, str]:
    """Add an identity self-map for every value that isn't itself a key --
    a lemma must lemmatize to itself, not fall through to the OOV fallbacks
    (et shipped 24,468 such values). Runs after value normalization; existing
    keys are never overwritten."""
    out = dict(mydict)
    added = 0
    for value in mydict.values():
        if (
            value not in out
            and _reachable_key(value)
            and any(ch.isalpha() for ch in value)
        ):
            out[value] = value
            added += 1
    if added:
        LOGGER.info("value selfmaps: added %d identity entries", added)
    return out


def _apply_build_normalization(mydict: dict[str, str], langcode: str) -> dict[str, str]:
    """Apply BUILD_NORMALIZATION[langcode] in the one order that's safe:
    value_fold (rewrite values in place) -> value_script_fix (script-
    consistency on the now-folded values) -> key_alias (copy the corrected
    value under a folded key twin, or replace it -- see drop_folded_keys).
    A no-op for any language with no entry."""
    entry = BUILD_NORMALIZATION.get(langcode)
    if entry is None:
        return mydict
    if entry.value_fold is not None:
        mydict = _fold_values(mydict, entry.value_fold)
    if entry.value_script_fix is not None:
        mydict = _fix_value_scripts(mydict, entry.value_script_fix)
    if entry.key_alias is not None:
        mydict = _add_key_aliases(
            mydict, entry.key_alias, drop_original=entry.drop_folded_keys
        )
    return mydict


def _shipped_str_dict(langcode: str) -> dict[str, str]:
    """The currently installed shipped dict, decoded bytes->str for building."""
    return {
        k.decode(): v.decode() for k, v in _load_dictionary_from_disk(langcode).items()
    }


def _report_tokenizer_reachability(mydict: Mapping[str, str], langcode: str) -> None:
    """Warn about keys the tokenizer never yields as one token (reported,
    not dropped: they still serve lemmatize()/is_known())."""
    unreachable = [k for k in mydict if simple_tokenizer(k) != [k]]
    if unreachable:
        LOGGER.info(
            "%s: %d of %d keys unreachable via the tokenizer (e.g. %s)",
            langcode,
            len(unreachable),
            len(mydict),
            ", ".join(sorted(unreachable)[:5]),
        )


def _compose_base(langcode: str, listpath: str | None = None) -> dict[str, str]:
    """Pre-layer half of the pipeline: the cleaned base wordlist or installed
    dict. Split out so build_override composes it once, layers it twice."""
    shipped = langcode in dictionary_factory.SUPPORTED_LANGUAGES
    if listpath is None:
        if not shipped:
            raise ValueError(
                f"no shipped dictionary for {langcode!r}: pass a wordlist "
                "directory (listpath) to ingest a new language"
            )
        return _clean_base(_shipped_str_dict(langcode))
    listdir = Path(listpath)
    if not listdir.is_absolute():
        listdir = Path(__file__).parent / listdir
    mydict = _read_dict(listdir / f"{langcode}.txt", langcode)
    if shipped:
        mydict.update(_clean_base(_shipped_str_dict(langcode)))
    return mydict


def _compose_from_base(
    base: dict[str, str], langcode: str, overrides_dir: Path | None = None
) -> dict[str, str]:
    """The post-base half of the pipeline: layers, scrub, normalization,
    selfmaps, junk filter."""
    mydict = _apply_layers(base, langcode, overrides_dir)
    mydict = _scrub(mydict)
    mydict = _apply_build_normalization(mydict, langcode)
    mydict = _ensure_value_selfmaps(mydict)
    # LAST, after selfmaps: planted identity keys for junk values must be
    # filtered too (needs identity-aware predicates, _foreign_script_entry).
    kept = _drop_junk_keys(mydict, langcode)
    if len(kept) < len(mydict):
        override_path = (overrides_dir or OVERRIDES_DIR) / f"{langcode}.tsv"
        if override_path.exists():
            # Reviewed overrides outrank the junk predicates (bg "II" ->
            # "втори" is deliberate); frontcode sorts, so re-adding is stable.
            dropped = mydict.keys() - kept.keys()
            casualties = _layer_entries(override_path, langcode).keys() & dropped
            for key in casualties:
                kept[key] = mydict[key]
            if casualties:
                LOGGER.info(
                    "%s: restored %d reviewed override entries the junk "
                    "filter had dropped: %s",
                    langcode,
                    len(casualties),
                    sorted(casualties)[:5],
                )
    return kept


def _compose_dictionary(
    langcode: str,
    listpath: str | None = None,
    overrides_dir: Path | None = None,
) -> dict[str, str]:
    """The full build pipeline (see module docstring) as one in-memory step.

    No `listpath`: routine rebuild over the installed dictionary. With
    `listpath` (a directory holding <langcode>.txt): wordlist ingestion,
    installed mappings still winning shared keys. SUPPORTED_LANGUAGES is
    read from the factory at call time so a test's monkeypatch is honored."""
    return _compose_from_base(
        _compose_base(langcode, listpath), langcode, overrides_dir
    )


def _build_dictionary(
    langcode: str = "en",
    listpath: str | None = None,
    filepath: str | None = None,
    in_place: bool = False,
) -> None:
    mydict = _compose_dictionary(langcode, listpath)
    if filepath is None:
        # in_place overwrites the shipped data the runtime loads (read at call
        # time so a test's DATA_FOLDER monkeypatch is honored); else training/output/
        if in_place:
            directory = dictionary_factory.DATA_FOLDER
        else:
            directory = Path(__file__).parent / "output"
            directory.mkdir(parents=True, exist_ok=True)
        filepath = str(directory / f"{langcode}.plzma")
    _report_tokenizer_reachability(mydict, langcode)
    # str->bytes only at the edge: frontcode is the runtime (bytes) boundary.
    encoded = {k.encode(): v.encode() for k, v in mydict.items()}
    reverse_key = langcode in FRONTCODE_REVERSE_KEY_LANGS
    Path(filepath).write_bytes(frontcode.encode(encoded, reverse_key=reverse_key))
    LOGGER.debug("%s %s", langcode, len(mydict))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write into the installed simplemma package's data directory, "
        "overwriting shipped dictionaries. Without this flag, output goes "
        "to training/output/ instead.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    for listcode in sorted(SUPPORTED_LANGUAGES):
        _build_dictionary(listcode, in_place=args.in_place)
