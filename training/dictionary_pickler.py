"""
Build a language's runtime lemmatization dictionary (a form->lemma map).

Pipeline: a BASE (one of three sources) is composed with optional per-language
layers, cleaned, and serialized:

    base  ->  _apply_layers (fill, shipped, override)  ->  _scrub  ->  frontcode

The base comes from `_build_dictionary(base=...)` / the CLI `--base` flag:
  - fresh:   `_read_dict` resolves one lemma per form from a raw wordlist
             (lemma<TAB>word lines, duplicate attestations = evidence).
  - shipped: the installed .plzma decoded verbatim.
  - merged:  fresh base with the shipped map layered on top.

Cleaning has two named key invariants (see _valid_key / _reachable_key): the
strict one filters machine sources (base/fill), the plain one is the universal
post-layer guard; reviewed overrides are exempt from the strict filter because
they carry deliberate elisions (e.g. ro "de-").

Output: the front-coded, lzma-compressed .plzma the runtime loads (see
frontcode.py); `frontcode.load` also still reads the legacy pre-v2.0 pickles.
"""

import argparse
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries import dictionary_factory, frontcode
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    _load_dictionary_from_disk,
)
from simplemma.utils import levenshtein_dist, normalize_token
from training.clean_wordlist import check_field, normalize, read_pairs

# Swahili inflection is prefixal, so a lemma's forms share an ENDING not a
# start; front-coding the reversed bytes exposes that shared structure.
FRONTCODE_REVERSE_KEY_LANGS = {"sw"}

# Optional per-language source layers merged by _apply_layers (precedence:
# overrides > shipped (only with merge_shipped) > base wordlist > fill).
OVERRIDES_DIR = Path(__file__).parent / "overrides"
FILL_DIR = Path(__file__).parent / "fill"

LOGGER = logging.getLogger(__name__)

# Punctuation a tokenizer never yields inside one token: a comma/colon/star/
# slash/plus/underscore anywhere, or a leading/trailing hyphen (affix fragment).
# Checked per field (form and lemma), so a hyphen affix in either column is caught.
FIELD_PUNCT = re.compile(r"[,:*/\+_]|.+-$|^-.+")


def _collect_candidates(
    filepath: str, langcode: str
) -> tuple[dict[str, Counter[str]], set[str]]:
    """First pass: filter input lines, counting each (form, lemma) pair as evidence.

    Per-line diagnostics (wrong format, rule mismatch) are DEBUG: opt-in for a
    maintainer inspecting one build, off in the default logging config, and the
    expensive rule call is skipped unless DEBUG is enabled."""
    diagnose = LOGGER.isEnabledFor(logging.DEBUG)
    candidates: defaultdict[str, Counter[str]] = defaultdict(Counter)
    lemmas: set[str] = set()
    with open(filepath, encoding="utf-8") as filehandle:
        for line in filehandle:
            # NFC at the choke point: runtime lookups NFC-normalize, so keys
            # must be NFC no matter how the input list was prepared.
            columns = [normalize_token(c) for c in line.strip().split("\t")]
            # invalid: wrong shape or empty lemma
            if len(columns) != 2 or not columns[0]:
                LOGGER.debug("wrong format: %s", line.strip())
                continue
            # drop a field the tokenizer could never yield as one token (space
            # or affix/punctuation) or that carries mojibake/control chars --
            # checked per field so a hyphen affix in EITHER column is caught.
            if any(
                " " in c or FIELD_PUNCT.search(c) or check_field(c) for c in columns
            ):
                continue
            # length difference
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


def _resolve_candidates(
    candidates: dict[str, Counter[str]],
    lemmas: set[str],
) -> dict[bytes, bytes]:
    """Second pass: pick one lemma per form (most attestations, then distance)."""
    diagnose = LOGGER.isEnabledFor(logging.DEBUG)
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
    # A dictionary headword is its own lemma: force identity so a noisy wordlist
    # line ("W is a form of X") can't reduce a valid lemma W into another
    # paradigm. Measured net-positive on every language gated (et/sk/lt +1-2pp,
    # bg/uk +6pp, nl +17pp) -- the old per-language BUFFER_HACK set was arbitrary
    # (it excluded da/nl, its two biggest beneficiaries).
    for word in lemmas:
        mydict[word] = word
    # convert to bytestrings; no need to sort, frontcode.encode sorts by key
    return {k.encode("utf-8"): v.encode("utf-8") for k, v in mydict.items()}


def _read_dict(filepath: str, langcode: str) -> dict[bytes, bytes]:
    candidates, lemmas = _collect_candidates(filepath, langcode)
    mydict = _resolve_candidates(candidates, lemmas)
    LOGGER.debug("%s: %d entries", langcode, len(mydict))
    return mydict


def _load_dict(langcode: str, listpath: str = "lists") -> dict[bytes, bytes]:
    # an absolute listpath (as tests pass) discards the training-dir prefix per
    # pathlib join semantics; a relative one resolves under training/.
    filepath = Path(__file__).parent / listpath / f"{langcode}.txt"
    return _read_dict(str(filepath), langcode)


def _layer_entries(path: Path) -> dict[bytes, bytes]:
    """A curated lemma<TAB>form layer file as a bytes form->lemma mapping.

    read_pairs enforces the shared key hygiene (NFC, no empty/junk field, no
    conflicting duplicate form) and fails loud on corruption. The one skip
    here is policy, not corruption: a multi-word form carries a space, which
    the tokenizer never yields as a single token (e.g. Wikidata lexemes like
    'top hat'), so it is an unreachable key."""
    pairs = read_pairs(path)
    entries = {
        form.encode(): lemma.encode()
        for form, lemma in pairs.items()
        if " " not in form
    }
    if len(entries) < len(pairs):
        LOGGER.info(
            "%s: skipped %d unreachable spaced forms",
            path.name,
            len(pairs) - len(entries),
        )
    return entries


def _apply_layers(
    base: dict[bytes, bytes], langcode: str, merge_shipped: bool = False
) -> dict[bytes, bytes]:
    """Merge the optional per-language source layers into the base wordlist
    dict. Precedence: overrides > shipped > base > fill. Fill (e.g. Wikidata)
    never displaces a base entry; reviewed overrides always win.

    merge_shipped (base="merged", for a fresh re-extraction): layer the
    currently installed shipped dict over the fresh base so its curated mappings
    survive -- the fresh wordlist only ADDS keys, existing mappings change only
    via the reviewed override. UD gate evidence (el) shows the accumulated
    shipped lemmas beat fresh single-dump Wiktionary on shared keys."""
    merged = dict(base)
    fill_path = FILL_DIR / f"{langcode}.tsv"
    if fill_path.exists():
        # fill is machine-extracted (Wikidata), so unlike reviewed overrides it
        # gets the same aggressive key hygiene as the base (suffix lexemes like
        # "-al" are unreachable keys).
        for form, lemma in _clean_base(_layer_entries(fill_path)).items():
            merged.setdefault(form, lemma)
        LOGGER.info("%s: fill layer applied -> %s entries", langcode, len(merged))
    if merge_shipped:
        merged.update(_clean_base(_load_dictionary_from_disk(langcode)))
        LOGGER.info("%s: shipped layer applied -> %s entries", langcode, len(merged))
    override_path = OVERRIDES_DIR / f"{langcode}.tsv"
    if override_path.exists():
        merged.update(_layer_entries(override_path))
        LOGGER.info("%s: override layer applied -> %s entries", langcode, len(merged))
    return merged


# Wiktionary template placeholders that leaked into old dicts as "lemmas".
_PLACEHOLDER_VALUES = {"prpers"}


def _valid_key(key: str) -> bool:
    """Universal key invariant, checked post-layer: NFC (normalize_token, the
    exact canonicalization runtime queries get) and free of control/mojibake
    chars. Deliberately NOT clean_wordlist.normalize: that also folds curly
    quotes, which runtime lookups keep, so folding here would silently drop
    reachable keys (mk "к’смет") and reviewed override forms."""
    return normalize_token(key) == key and not check_field(key)


def _reachable_key(key: str) -> bool:
    """Stricter invariant for MACHINE sources (base wordlist, Wikidata fill):
    additionally no space or punctuation a tokenizer never yields as one token.
    Reviewed overrides are exempt -- they carry deliberate elisions (ro "de-")."""
    return _valid_key(key) and " " not in key and not FIELD_PUNCT.search(key)


def _clean_base(base: dict[bytes, bytes]) -> dict[bytes, bytes]:
    """Drop unreachable keys from a machine source used as a base or layer.
    Pre-layer ONLY: any override-originated entry this would drop is re-applied
    afterwards by _apply_layers, so it never touches reviewed override content."""
    out = {k: v for k, v in base.items() if _reachable_key(k.decode())}
    if len(out) < len(base):
        LOGGER.info("clean_base: dropped %d unreachable keys", len(base) - len(out))
    return out


def _junk_entry(key: str, value: str) -> bool:
    """A non-identity entry whose value is an affix fragment or carries no
    letters, or whose key is a symbol mapped to a word (bg ":" -> "на", mined
    UD noise). Junk from Wiktionary affix tables (schaft -> -schaft). Identity
    entries stay: dropping "&" -> "&" or "10" -> "10" only breaks is_known().
    Deliberately narrow -- commas/underscores appear in legit compound lemmas."""
    if value == key:
        return False
    return (
        value.startswith("-")
        or value.endswith("-")
        or not any(ch.isalpha() for ch in value)
        or not any(ch.isalpha() for ch in key)
    )


def _scrub(mydict: dict[bytes, bytes]) -> dict[bytes, bytes]:
    """Final post-layer pass over the composed dict. Drops keys failing the
    universal invariant (unreachable), normalizes each value and drops the
    entry if the value is still junk, an affix fragment, or a placeholder.
    Uses _valid_key not _reachable_key: it runs AFTER overrides, whose elisions
    must survive."""
    out: dict[bytes, bytes] = {}
    dropped_key = fixed_val = dropped_val = 0
    for k, v in mydict.items():
        ks = k.decode()
        if not _valid_key(ks):
            dropped_key += 1
            continue
        nv = normalize(v.decode())[0]
        if (
            not nv
            or check_field(nv)
            or nv in _PLACEHOLDER_VALUES
            or _junk_entry(ks, nv)
        ):
            dropped_val += 1
            continue
        fixed_val += nv != v.decode()
        out[k] = nv.encode()
    if dropped_key or dropped_val or fixed_val:
        LOGGER.info(
            "scrub: dropped %d junk keys, dropped %d junk values, fixed %d values",
            dropped_key,
            dropped_val,
            fixed_val,
        )
    return out


BASE_MODES = ("fresh", "shipped", "merged")


def _build_dictionary(
    langcode: str = "en",
    listpath: str = "lists",
    filepath: str | None = None,
    in_place: bool = False,
    base: str = "fresh",
) -> None:
    # base source: "fresh" rebuilds from the wordlist via _read_dict; "shipped"
    # reuses the installed .plzma decoded verbatim; "merged" is a fresh base with
    # the shipped map layered on top so its curated mappings win shared keys.
    if base not in BASE_MODES:
        raise ValueError(f"unknown base mode {base!r}, expected one of {BASE_MODES}")
    source = (
        _clean_base(_load_dictionary_from_disk(langcode))
        if base == "shipped"
        else _load_dict(langcode, listpath)
    )
    mydict = _scrub(_apply_layers(source, langcode, merge_shipped=(base == "merged")))
    if filepath is None:
        # in_place overwrites the shipped data the runtime loads (read at call
        # time so a test's DATA_FOLDER monkeypatch is honored); else training/output/
        if in_place:
            directory = dictionary_factory.DATA_FOLDER
        else:
            directory = Path(__file__).parent / "output"
            directory.mkdir(parents=True, exist_ok=True)
        filepath = str(directory / f"{langcode}.plzma")
    reverse_key = langcode in FRONTCODE_REVERSE_KEY_LANGS
    Path(filepath).write_bytes(frontcode.encode(mydict, reverse_key=reverse_key))
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
