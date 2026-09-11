"""Rebuild a language's runtime lemmatization dictionary (a form->lemma map).

Pipeline: base -> overrides -> _scrub -> _apply_build_normalization ->
_ensure_value_selfmaps -> _drop_junk_keys -> frontcode. Plain str dicts
throughout; bytes only at the two edges.

Base: the installed dictionary itself (pinned artifact, routine rebuilds
idempotent). New wordlist data enters via wordlist_ingest.py.

Key invariants: _valid_key (universal post-layer guard) vs _reachable_key
(stricter, machine sources only; overrides exempt for deliberate elisions
like ro "de-").
"""

import argparse
import logging
import re
import sys
import unicodedata
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from simplemma.tokenizer import simple_tokenizer
from simplemma.strategies.dictionaries import dictionary_factory
from training.frontcode_encode import _encode as _frontcode_encode
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    _load_dictionary_from_disk,
)
from simplemma.utils import canonicalize_token, normalize_token
from training.build_lang_config import BUILD_NORMALIZATION, JUNK_ENTRY_PREDICATES
from training.clean_wordlist import canonicalize, check_field, read_pairs

# sw inflection is prefixal (forms share an ending, not a start), so
# front-coding uses reversed-byte keys here.
FRONTCODE_REVERSE_KEY_LANGS = {"sw"}

# Reviewed per-language layer, wins every key it names.
OVERRIDES_DIR = Path(__file__).parent / "overrides"

LOGGER = logging.getLogger(__name__)

# Fields dropped from dictionary entries: punctuation the tokenizer splits on
# (comma/colon/slash/plus), an edge hyphen (affix fragment), and star/
# underscore (tokenizer-reachable word-body chars, but Wiktionary artifacts in
# wordlists; `_`-joined tokens are served by hyphen removal). Hebrew maqaf
# (U+05BE) is Wiktionary's hyphen for bound-morpheme headwords (ב־).
FIELD_PUNCT = re.compile(r"[,:*/\+_]|.+[-־]$|^[-־].+")


def _canon(text: str, langcode: str) -> str:
    """Runtime key space: per-language canon, then NFC again (canon can
    strand a stacked combining mark, la 'Boō̈tēs')."""
    return normalize_token(canonicalize_token(text, langcode))


def _is_single_token(text: str) -> bool:
    """True if `text` is acceptable as ONE dictionary token: no space and no
    FIELD_PUNCT (mostly tokenizer reachability, partly policy -- see above).
    The orthogonal 'not mojibake/control' check is check_field; both callers
    (wordlist_ingest on raw columns, _reachable_key via _valid_key) pair
    this with it."""
    return " " not in text and not FIELD_PUNCT.search(text)


def _layer_entries(path: Path, langcode: str) -> dict[str, str]:
    """A curated lemma<TAB>form layer file as a form->lemma mapping,
    canonicalized like the base wordlist (wordlist_ingest) so a reviewed
    file can't ship an unreachable dead key.

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
        LOGGER.info(
            "%s: skipped %d entries with a spaced form or lemma",
            path.name,
            len(pairs) - len(spaceless),
        )
    entries: dict[str, str] = {}
    for form, lemma in spaceless.items():
        cform = _canon(form, langcode)
        clemma = _canon(lemma, langcode)
        if cform in entries and entries[cform] != clemma:
            raise ValueError(
                f"{path}: two entries fold to the same canonical form "
                f"{cform!r} with different lemmas ({entries[cform]!r} vs "
                f"{clemma!r}) -- reviewed entries must agree once folded "
                f"to the runtime key space"
            )
        entries[cform] = clemma
    return entries


# Wiktionary template placeholders that leaked into old dicts as "lemmas".
_PLACEHOLDER_VALUES = {"prpers"}


def _valid_key(key: str) -> bool:
    """Universal key invariant, checked post-layer: normalize_token-stable (NFC,
    straight apostrophes -- the exact normalization runtime queries get) and
    free of control/mojibake chars. Deliberately NOT clean_wordlist.canonicalize
    (applied to wordlist input only)."""
    return normalize_token(key) == key and not check_field(key)


def _reachable_key(key: str) -> bool:
    """Stricter invariant for MACHINE sources (wordlists):
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
    that are junk/placeholder after canonicalize."""
    out: dict[str, str] = {}
    dropped_key = fixed_val = dropped_val = 0
    for k, v in mydict.items():
        if not _valid_key(k):
            dropped_key += 1
            continue
        nv = canonicalize(v)
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


def _drop_junk_keys(mydict: dict[str, str], langcode: str) -> dict[str, str]:
    """Drop entries matching langcode's JUNK_ENTRY_PREDICATES entry; a
    no-op for any other language. Each side's script set is computed once
    here and handed to the predicate."""
    predicate = JUNK_ENTRY_PREDICATES.get(langcode)
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
    """The installed shipped dict keyed in the runtime key space (_canon);
    keys folding together with different values are a data bug."""
    out: dict[str, str] = {}
    for key, value in _load_dictionary_from_disk(langcode).items():
        ckey, v = _canon(key.decode(), langcode), value.decode()
        if out.setdefault(ckey, v) != v:
            raise ValueError(
                f"{langcode}: shipped key {key.decode()!r} folds to {ckey!r} "
                f"with a different value than its twin -- fix via an override"
            )
    return out


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


def _compose_base(langcode: str) -> dict[str, str]:
    """The cleaned installed dict (SUPPORTED_LANGUAGES read from the factory
    at call time so a test's monkeypatch is honored)."""
    if langcode not in dictionary_factory.SUPPORTED_LANGUAGES:
        raise ValueError(
            f"no shipped dictionary for {langcode!r}: ingest a wordlist first "
            "(training.wordlist_ingest)"
        )
    return _clean_base(_shipped_str_dict(langcode))


def _compose_from_base(
    base: dict[str, str], langcode: str, overrides_dir: Path | None = None
) -> dict[str, str]:
    """The post-base half of the pipeline: overrides, scrub, normalization,
    selfmaps, junk filter."""
    override_path = (overrides_dir or OVERRIDES_DIR) / f"{langcode}.tsv"
    overrides = (
        _layer_entries(override_path, langcode) if override_path.exists() else {}
    )
    mydict = {**base, **overrides}
    if overrides:
        LOGGER.info("%s: override layer applied -> %s entries", langcode, len(mydict))
    mydict = _scrub(mydict)
    mydict = _apply_build_normalization(mydict, langcode)
    mydict = _ensure_value_selfmaps(mydict)
    # LAST, after selfmaps: planted identity keys for junk values must be
    # filtered too (needs identity-aware predicates, _foreign_script_entry).
    kept = _drop_junk_keys(mydict, langcode)
    if len(kept) < len(mydict):
        # Reviewed overrides outrank the junk predicates (bg "II" ->
        # "втори" is deliberate); frontcode sorts, so re-adding is stable.
        casualties = overrides.keys() & (mydict.keys() - kept.keys())
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


def _compose_dictionary(langcode: str) -> dict[str, str]:
    """The full routine rebuild (see module docstring) as one in-memory step."""
    return _compose_from_base(_compose_base(langcode), langcode)


def _encode_dictionary(mydict: dict[str, str], langcode: str) -> bytes:
    """Ship encoding: front-coded + lzma; str->bytes only at this edge."""
    encoded = {k.encode(): v.encode() for k, v in mydict.items()}
    return _frontcode_encode(
        encoded, reverse_key=langcode in FRONTCODE_REVERSE_KEY_LANGS
    )


def _write_dictionary(
    mydict: dict[str, str], langcode: str, filepath: str | None, in_place: bool
) -> None:
    """Encode and write to `filepath`, else the installed data dir (in_place)
    or training/output/."""
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
    Path(filepath).write_bytes(_encode_dictionary(mydict, langcode))
    LOGGER.debug("%s %s", langcode, len(mydict))


def _build_dictionary(
    langcode: str, filepath: str | None = None, in_place: bool = False
) -> None:
    _write_dictionary(_compose_dictionary(langcode), langcode, filepath, in_place)


def _drifted_languages(langs: list[str]) -> list[str]:
    """Languages whose recompose is not byte-identical to the shipped plzma
    (zero drift is the invariant: a difference means a pipeline change
    rewrites shipped data)."""
    drifted = []
    for lang in langs:
        mydict = _compose_dictionary(lang)
        shipped = (dictionary_factory.DATA_FOLDER / f"{lang}.plzma").read_bytes()
        drift = _encode_dictionary(mydict, lang) != shipped
        LOGGER.info(
            "%s: %s (%d entries)", lang, "DRIFT" if drift else "ok", len(mydict)
        )
        if drift:
            drifted.append(lang)
    return drifted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("langs", nargs="*", help="default: every shipped language")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write into the installed simplemma package's data directory, "
        "overwriting shipped dictionaries. Without this flag, output goes "
        "to training/output/ instead.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 listing languages that do not recompose "
        "byte-identically (~15 min for all, seconds per language).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    codes = args.langs or sorted(SUPPORTED_LANGUAGES)
    if args.check:
        drifted = _drifted_languages(codes)
        if drifted:
            sys.exit(f"idempotence DRIFT in {len(drifted)}/{len(codes)}: {drifted}")
        print(f"all {len(codes)} dictionaries recompose byte-identically")
    else:
        for listcode in codes:
            _build_dictionary(listcode, in_place=args.in_place)
