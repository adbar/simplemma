"""Rebuild a language's runtime form to lemma dictionary from the installed one.

Pipeline: base, overrides, scrub, build normalization, value selfmaps, junk
filter, frontcode.
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

# sw inflection is prefixal, so forms share an ending rather than a start.
FRONTCODE_REVERSE_KEY_LANGS = {"sw"}

OVERRIDES_DIR = Path(__file__).parent / "overrides"

LOGGER = logging.getLogger(__name__)

# Tokenizer split chars, Wiktionary artifacts (* _) and edge hyphens or maqaf (affixes).
FIELD_PUNCT = re.compile(r"[,:*/\+_]|.+[-־]$|^[-־].+")


def _canon(text: str, langcode: str) -> str:
    """Runtime key space: canon then NFC, since canon can strand a combining mark."""
    return normalize_token(canonicalize_token(text, langcode))


def _layer_entries(path: Path, langcode: str) -> dict[str, str]:
    """A curated lemma<TAB>form file as a canonicalized form to lemma mapping.

    Entries with a spaced form or lemma are skipped."""
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


# Wiktionary template placeholders.
_PLACEHOLDER_VALUES = {"prpers"}


def _valid_key(key: str) -> bool:
    """Key is normalize_token-stable and free of control or mojibake chars."""
    return normalize_token(key) == key and not check_field(key)


def _reachable_key(key: str) -> bool:
    """_valid_key plus no space or FIELD_PUNCT, for machine sources only."""
    return _valid_key(key) and " " not in key and not FIELD_PUNCT.search(key)


def _clean_base(base: dict[str, str]) -> dict[str, str]:
    """Drop unreachable keys from a machine source, before overrides apply."""
    out = {k: v for k, v in base.items() if _reachable_key(k)}
    if len(out) < len(base):
        LOGGER.info("clean_base: dropped %d unreachable keys", len(base) - len(out))
    return out


def _junk_entry(key: str, value: str) -> bool:
    """Non-identity entry with an affix-fragment value or a letterless side."""
    if value == key:
        return False
    return (
        value.startswith(("-", "־"))  # hyphen or Hebrew maqaf
        or value.endswith(("-", "־"))
        or not any(ch.isalpha() for ch in value)
        or not any(ch.isalpha() for ch in key)
    )


def _scrub(mydict: dict[str, str]) -> dict[str, str]:
    """Drop invalid keys and junk values, canonicalizing the rest."""
    out: dict[str, str] = {}
    dropped_key = fixed_val = dropped_val = 0
    for k, v in mydict.items():
        if not _valid_key(k):
            dropped_key += 1
            continue
        nv = canonicalize(v)
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
    """Script name of one alphabetic char, else None."""
    if not ch.isalpha():
        return None
    try:
        return unicodedata.name(ch).split()[0]
    except ValueError:
        return None


def _script_classes(word: str) -> frozenset[str]:
    """Script names of `word`'s letters. Empty does not mean foreign."""
    return frozenset(s for s in map(_char_script, word) if s is not None)


def _drop_junk_keys(mydict: dict[str, str], langcode: str) -> dict[str, str]:
    """Drop entries matching the language's JUNK_ENTRY_PREDICATES entry."""
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


_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def _fix_value_scripts(
    mydict: dict[str, str], table: Mapping[int, str]
) -> dict[str, str]:
    """Transliterate a Cyrillic value on a Cyrillic-free key, unless partial."""
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
    """Add a folded-key alias per entry, or replace the key with `drop_original`.

    An existing exact key is never overwritten."""
    out = dict(mydict)
    for key, value in mydict.items():
        # NFC again: folding can strand a combining mark.
        alias = normalize_token(key.translate(table))
        # A mark-only key folds to "".
        if alias and alias != key:
            out.setdefault(alias, value)
            if drop_original:
                del out[key]
    return out


def _ensure_value_selfmaps(mydict: dict[str, str]) -> dict[str, str]:
    """Add an identity entry for every value that isn't already a key."""
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
    """Apply BUILD_NORMALIZATION[langcode]: value fold, script fix, key alias."""
    entry = BUILD_NORMALIZATION.get(langcode)
    if entry is None:
        return mydict
    if entry.value_fold is not None:
        table = entry.value_fold
        mydict = {k: normalize_token(v.translate(table)) for k, v in mydict.items()}
    if entry.value_script_fix is not None:
        mydict = _fix_value_scripts(mydict, entry.value_script_fix)
    if entry.key_alias is not None:
        mydict = _add_key_aliases(
            mydict, entry.key_alias, drop_original=entry.drop_folded_keys
        )
    return mydict


def _shipped_str_dict(langcode: str) -> dict[str, str]:
    """The installed dict in the runtime key space, raising on conflicting folds."""
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
    """Report keys the tokenizer never yields as one token."""
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
    """The cleaned installed dict."""
    if langcode not in dictionary_factory.SUPPORTED_LANGUAGES:
        raise ValueError(
            f"no shipped dictionary for {langcode!r}: ingest a wordlist first "
            "(training.wordlist_ingest)"
        )
    return _clean_base(_shipped_str_dict(langcode))


def _compose_from_base(
    base: dict[str, str], langcode: str, overrides_dir: Path | None = None
) -> dict[str, str]:
    """The pipeline after the base."""
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
    # After selfmaps, so identity keys planted for junk values get dropped too.
    kept = _drop_junk_keys(mydict, langcode)
    if len(kept) < len(mydict):
        # Reviewed overrides outrank the junk predicates.
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
    """The full rebuild in memory."""
    return _compose_from_base(_compose_base(langcode), langcode)


def _encode_dictionary(mydict: dict[str, str], langcode: str) -> bytes:
    """Front-coded and lzma-compressed bytes."""
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
    """Languages whose rebuild is not byte-identical to the shipped file."""
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
