"""Build a language's runtime lemmatization dictionary (a form->lemma map).

Pipeline: _base_source -> _apply_layers (fill, override) -> _scrub ->
_apply_build_normalization -> _ensure_value_selfmaps -> _drop_junk_keys ->
frontcode. Plain str dicts throughout; bytes only at the two edges.

Base modes (--base): fresh (rebuild from wordlist, duplicate lines = evidence),
shipped (installed .plzma verbatim), merged (fresh + shipped layered on top,
shipped wins shared keys).

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
# base > fill; base may already fold in the shipped dict, see _base_source).
OVERRIDES_DIR = Path(__file__).parent / "overrides"
FILL_DIR = Path(__file__).parent / "fill"

# Languages whose Wikidata fill ships, gated by assess_wikidata_fill.py.
# Enforced here because fill/ is gitignored -- a stale local TSV must fail
# loud. Gate-rejected: fr/it/tr (cross-treebank regressions), id (WD cites
# the meN- active form as lemma, shipped dict uses the bare root), fa
# (verb-stem noise), se (+0.0000pp, nothing to add); nb has no UD treebank.
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
            columns = [
                canonicalize_token(normalize_token(c), langcode)
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


# Languages where a headword's identity must NOT override an attested
# form-of mapping: grc (ἀκούσας is both its own headword and a form of
# ἀκούω; removing this measured -3.8/-7.8pp token, 2026-08 -- the universal
# self-only-lemma softening below does NOT subsume it). Force-identity stays
# the default -- gate-proven net-positive elsewhere (et/sk/lt +1-2pp, bg/uk
# +6pp, nl +17pp). A per-word ar predicate (article-prefixed headwords) was
# DELETED 2026-08: measured +0.000pp token AND type on PADT (40 entries)
# once self-only lemmas became soft anyway.
IDENTITY_SOFT_LANGS = frozenset({"grc"})


# Break an attestation TIE by paradigm size (distinct forms attested for the
# lemma) before Levenshtein distance: distance alone lets a rare lexeme win an
# ultra-frequent form (grc ἦν -> ἠμί instead of εἰμί). Per-language, gated on
# every UD test split (2026-08: grc +1.2/+1.4pp .. et +0.04; gl/lt FAILED,
# ar/uk noise, and the prior LOSES elsewhere (sl -0.7, da -0.6) -- never make
# it the default).
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
    # A headword is its own lemma: force identity so a noisy wordlist line
    # can't reduce it into another paradigm. Soft (setdefault only):
    # IDENTITY_SOFT_LANGS entirely, plus lemmas attested ONLY by their own
    # identity line (forcing those measured -1.3..-2.2 / lv -1.8..-2.6pp).
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


def _layer_entries(path: Path, langcode: str) -> dict[str, str]:
    """A curated lemma<TAB>form layer file as a form->lemma mapping,
    canonicalized like the base wordlist (_collect_candidates) so a
    reviewed file can't ship an unreachable dead key.

    read_pairs enforces key hygiene and fails loud on corruption. Skipping a
    multi-word form (e.g. Wikidata 'top hat') is policy, not corruption --
    the tokenizer never yields it as a single token, so it's unreachable."""
    pairs = read_pairs(path)
    spaceless = {form: lemma for form, lemma in pairs.items() if " " not in form}
    if len(spaceless) < len(pairs):
        LOGGER.info(
            "%s: skipped %d unreachable spaced forms",
            path.name,
            len(pairs) - len(spaceless),
        )
    entries: dict[str, str] = {}
    for form, lemma in spaceless.items():
        cform = canonicalize_token(form, langcode)
        clemma = canonicalize_token(lemma, langcode)
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
        for form, lemma in _clean_base(_layer_entries(fill_path, langcode)).items():
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
        if not nv or check_field(nv) or nv in _PLACEHOLDER_VALUES or _junk_entry(k, nv):
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


def _script_classes(word: str) -> frozenset[str]:
    """Every Unicode script name (the part of unicodedata.name before its
    first space, e.g. "CYRILLIC" from "CYRILLIC SMALL LETTER A") among
    `word`'s alphabetic characters. Empty for a non-alphabetic string
    (digits, punctuation) -- callers must not treat that as "foreign"."""
    out = set()
    for ch in word:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            continue
        out.add(name.split()[0])
    return frozenset(out)


def _is_foreign_script_value(key: str, value: str, allowed: frozenset[str]) -> bool:
    """_is_foreign_script_key with the arguments swapped: an English gloss
    leaked in as if it were the lemma (grc κάλαμος -> "plants")."""
    return _is_foreign_script_key(value, key, allowed)


def _is_foreign_script_key(key: str, value: str, allowed: frozenset[str]) -> bool:
    """True when `key` uses NO script in `allowed` while `value` uses one --
    the shape of a Wiktionary academic-transliteration or IPA row that leaked
    in as if it were a real word form (e.g. ar IPA "uð.ðu.ki.ruː" -> Arabic
    "اذكروا", grc Beta-code "hubrisin" -> Greek "ὑβρίς", bg/uk BGN/PCGN-style
    "rádost"/"zanos" -> Cyrillic). A key carrying ANY allowed-script letter
    (mixed script, e.g. hbs "atoмска") is never flagged -- only entirely
    foreign-scripted keys are. `allowed` need not be the language's ONLY
    real script: ms is genuinely biscriptal (Jawi legitimately resolves to
    the standard Rumi citation lemma) so `allowed={"ARABIC"}` there flags
    just the wrong direction (Latin key -> Jawi value), leaving the correct
    Jawi-key entries untouched."""
    ks, vs = _script_classes(key), _script_classes(value)
    return bool(ks) and bool(vs) and not (ks & allowed) and bool(vs & allowed)


# Per-language (key, value) -> drop predicates. Each entry is a verified,
# language-specific defect -- there is no universal "foreign script" or
# "digit-leading" rule (a digit-leading token is a real word in many
# languages: da "0-1-nederlaget", de "1-Cent-Münze", en "1000000", ga
# "1000ú", hu "10-es", sv "10-krona", all verified present in their shipped
# dicts; a Latin-script key is legitimate in most languages too).
_JUNK_ENTRY_PREDICATES: dict[str, Callable[[str, str], bool]] = {
    # uk: Wiktionary conjugation-table paradigm-class codes ("10a", "3°a",
    # the unrendered-template variant "3[°]a") + footnote leaks
    # ("¹Colloquial.") -- verified: every uk key starting with an ASCII or
    # superscript digit is this junk, zero are real Ukrainian words.
    # PLUS: BGN/PCGN-style scientific transliteration rows ("zanos" ->
    # "занос") -- Ukrainian running text is always Cyrillic.
    # PLUS: EVERY Latin+Cyrillic mixed-script key -- today only homoglyph
    # poisoning ("cказився" with Latin c), 15,828 fill entries, none with two
    # consecutive Latin letters. Broader than that evidence: a legitimate
    # Latin-segment word (IT-фахівець) would be dropped here silently, so
    # narrow to a homoglyph test if one is ever wanted.
    "uk": lambda k, v: (
        bool(re.match(r"^[\d¹²³]", k))
        or _is_foreign_script_key(k, v, frozenset({"CYRILLIC"}))
        or {"LATIN", "CYRILLIC"} <= _script_classes(k)
    ),
    # ar: IPA phonetic-transcription rows leaked in as word forms (syllable-
    # dot-separated, IPA symbols ʔ/ʕ/ˤ/θ) -- 98,864 shipped entries, ALL this
    # one shape. Arabic running text is always Arabic script.
    "ar": lambda k, v: _is_foreign_script_key(k, v, frozenset({"ARABIC"})),
    # grc: Beta-code/scientific romanization rows ("hubrisin" -> "ὑβρίς").
    # CYPRIOT and LINEAR (B) are kept allowed -- genuine rare alternate-
    # script attestations for early Greek, not Wiktionary citation noise.
    # The value direction catches English glosses shipped as lemmas
    # (κάλαμος -> "plants", πόσος -> "quantity").
    "grc": lambda k, v: (
        _is_foreign_script_key(k, v, frozenset({"GREEK", "CYPRIOT", "LINEAR"}))
        or _is_foreign_script_value(k, v, frozenset({"GREEK", "CYPRIOT", "LINEAR"}))
    ),
    # bg: BGN/PCGN-style scientific transliteration rows ("rádost" ->
    # "радост") -- Bulgarian running text is always Cyrillic.
    "bg": lambda k, v: _is_foreign_script_key(k, v, frozenset({"CYRILLIC"})),
    # hi: Perso-Arabic (Urdu-script) entries from Wiktionary's shared
    # Hindi/Urdu extraction -- Urdu is not a supported simplemma language
    # and real Hindi text is always Devanagari, so these are unreachable
    # regardless of Hindi/Urdu being the same spoken language.
    "hi": lambda k, v: _is_foreign_script_key(k, v, frozenset({"DEVANAGARI"})),
    # ms: genuinely biscriptal (Jawi legitimately resolves to the standard
    # Rumi citation lemma, 3,301 shipped entries, KEPT) -- but a Latin/Rumi
    # key must never resolve to a Jawi value (446 shipped entries did).
    "ms": lambda k, v: _is_foreign_script_key(k, v, frozenset({"ARABIC"})),
    # tl: Baybayin-script keys (via Wiktionary alt_of relations from Baybayin
    # headword pages -- the Baybayin FORMS-tag drop in kaikki_to_tsv doesn't
    # cover this path). Unlike ms's Jawi, Baybayin has no modern running-text
    # use, so the keys are dead weight (3,909 shipped entries, 5.4%).
    # Key-side check, not _is_foreign_script_key: 5 entries carry Baybayin
    # VALUES too and must also go.
    "tl": lambda k, v: "TAGALOG" in _script_classes(k),
    # he: Latin-script keys resolving to Hebrew values (transliterated proper
    # nouns, Latin abbreviations) -- Hebrew running text is Hebrew script.
    "he": lambda k, v: _is_foreign_script_key(k, v, frozenset({"HEBREW"})),
}


def _drop_junk_keys(mydict: dict[str, str], langcode: str) -> dict[str, str]:
    """Drop entries matching langcode's _JUNK_ENTRY_PREDICATES entry; a
    no-op for any other language."""
    predicate = _JUNK_ENTRY_PREDICATES.get(langcode)
    if predicate is None:
        return mydict
    return {k: v for k, v in mydict.items() if not predicate(k, v)}


# fa tashkeel/tatweel deletion (was 23.8% of keys) + Arabic-script ي/ك ->
# standard Persian ی/ک (was 41% of keys, 23% of values).
_FA_NORMALIZE: dict[int, int | None] = {
    **_ARABIC_MARKS,
    ord("ي"): ord("ی"),
    ord("ك"): ord("ک"),
}


def _mark_fold_table(marks: frozenset[int], keep: str = "") -> dict[int, str | None]:
    """Deletion of the given combining marks + every precomposed Latin/
    Cyrillic letter carrying one folded to its plain form, generated from
    unicodedata (hand-typed tables shipped wrong twice this arc). `keep`
    protects letters whose precomposed form uses one of `marks`
    orthographically, not as pitch/length marking (e.g. hbs/sl ć: the acute
    is the letter c-acute, not pitch marking -- a naive strip would corrupt
    it to c)."""
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
    never create a collision -- unlike a symmetric fold or a key alias."""
    return {k: v.translate(table) for k, v in mydict.items()}


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
        alias = key.translate(table)
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


BASE_MODES = ("fresh", "shipped", "merged")


def _shipped_str_dict(langcode: str) -> dict[str, str]:
    """The currently installed shipped dict, decoded bytes->str for building."""
    return {
        k.decode(): v.decode() for k, v in _load_dictionary_from_disk(langcode).items()
    }


def _base_source(base: str, langcode: str, listpath: str) -> dict[str, str]:
    """The base the override/fill layers compose over:
    - fresh:   rebuild from the wordlist;
    - shipped: the installed .plzma decoded verbatim;
    - merged:  a fresh base with the shipped map layered on top so its curated
               mappings win shared keys (the fresh wordlist only ADDS keys)."""
    if base == "shipped":
        return _clean_base(_shipped_str_dict(langcode))
    listdir = Path(listpath)
    if not listdir.is_absolute():
        listdir = Path(__file__).parent / listdir
    source = _read_dict(listdir / f"{langcode}.txt", langcode)
    if base == "merged":
        source.update(_clean_base(_shipped_str_dict(langcode)))
    return source


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


def _compose_dictionary(
    langcode: str,
    listpath: str = "lists",
    base: str = "fresh",
    overrides_dir: Path | None = None,
) -> dict[str, str]:
    """The full build pipeline (see module docstring) as one in-memory step --
    the single place the stage chain lives, for _build_dictionary and for
    gating tools that need a candidate build without writing a file."""
    if base not in BASE_MODES:
        raise ValueError(f"unknown base mode {base!r}, expected one of {BASE_MODES}")
    mydict = _base_source(base, langcode, listpath)
    mydict = _apply_layers(mydict, langcode, overrides_dir)
    mydict = _scrub(mydict)
    mydict = _apply_build_normalization(mydict, langcode)
    mydict = _ensure_value_selfmaps(mydict)
    # LAST, after the selfmaps: an identity key planted for a junk value would
    # otherwise re-enter a dictionary this stage had just cleaned (verified
    # output-identical on every predicate language, so the move is free).
    return _drop_junk_keys(mydict, langcode)


def _build_dictionary(
    langcode: str = "en",
    listpath: str = "lists",
    filepath: str | None = None,
    in_place: bool = False,
    base: str = "fresh",
) -> None:
    mydict = _compose_dictionary(langcode, listpath, base)
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
    parser.add_argument(
        "--base",
        choices=BASE_MODES,
        default="fresh",
        help="Base source: 'fresh' rebuilds from the wordlist; 'shipped' reuses "
        "the installed .plzma verbatim; 'merged' is a fresh base with the shipped "
        "map layered on top (reads the installed dict, so run once from a clean "
        "checkout before --in-place overwrites it).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    for listcode in sorted(SUPPORTED_LANGUAGES):
        _build_dictionary(listcode, in_place=args.in_place, base=args.base)
