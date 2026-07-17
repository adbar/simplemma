"""Build a language's runtime lemmatization dictionary (a form->lemma map).

Pipeline: _base_source -> _apply_layers (fill, override) -> _scrub -> frontcode.
Plain str dicts throughout; bytes only at the two edges.

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
from collections import Counter, defaultdict
from pathlib import Path

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries import dictionary_factory, frontcode
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    _load_dictionary_from_disk,
)
from simplemma.utils import levenshtein_dist, normalize_token
from training.clean_wordlist import canonicalize, check_field, read_pairs

# sw inflection is prefixal (forms share an ending, not a start), so
# front-coding uses reversed-byte keys here.
FRONTCODE_REVERSE_KEY_LANGS = {"sw"}

# Per-language source layers merged by _apply_layers (precedence: overrides >
# base > fill; base may already fold in the shipped dict, see _base_source).
OVERRIDES_DIR = Path(__file__).parent / "overrides"
FILL_DIR = Path(__file__).parent / "fill"

# Languages whose Wikidata fill ships in v2.0 (gated by assess_wikidata_fill.py):
# fr/it/tr HELD (cross-treebank regressions), nb has no UD treebank. Enforced
# here because fill/ is gitignored -- a stale local TSV must fail loud.
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
# slash/plus/underscore anywhere, or a leading/trailing hyphen (affix fragment).
FIELD_PUNCT = re.compile(r"[,:*/\+_]|.+-$|^-.+")


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
            # NFC here: runtime lookups NFC-normalize, so keys must match.
            columns = [normalize_token(c) for c in line.strip().split("\t")]
            if len(columns) != 2 or not columns[0]:
                LOGGER.debug("wrong format: %s", line.strip())
                continue
            # drop fields a tokenizer could never yield as one token, or
            # carrying mojibake/control chars.
            if any(
                " " in c or FIELD_PUNCT.search(c) or check_field(c) for c in columns
            ):
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


def _resolve_candidates(
    candidates: dict[str, Counter[str]],
    lemmas: set[str],
) -> dict[str, str]:
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
    # A dictionary headword is its own lemma: force identity so a noisy
    # wordlist line can't reduce it into another paradigm. Measured
    # net-positive on every language gated (et/sk/lt +1-2pp, bg/uk +6pp,
    # nl +17pp).
    for word in lemmas:
        mydict[word] = word
    return mydict


def _read_dict(path: Path, langcode: str) -> dict[str, str]:
    """Resolve a raw ``lemma<TAB>form`` wordlist at `path` into a form->lemma dict."""
    candidates, lemmas = _collect_candidates(path, langcode)
    mydict = _resolve_candidates(candidates, lemmas)
    LOGGER.debug("%s: %d entries", langcode, len(mydict))
    return mydict


def _layer_entries(path: Path) -> dict[str, str]:
    """A curated lemma<TAB>form layer file as a form->lemma mapping.

    read_pairs enforces key hygiene and fails loud on corruption. Skipping a
    multi-word form (e.g. Wikidata 'top hat') is policy, not corruption --
    the tokenizer never yields it as a single token, so it's unreachable."""
    pairs = read_pairs(path)
    entries = {form: lemma for form, lemma in pairs.items() if " " not in form}
    if len(entries) < len(pairs):
        LOGGER.info(
            "%s: skipped %d unreachable spaced forms",
            path.name,
            len(pairs) - len(entries),
        )
    return entries


def _apply_layers(base: dict[str, str], langcode: str) -> dict[str, str]:
    """Merge the optional per-language source layers into the base dict.
    Precedence: overrides > base > fill; fill never displaces a base entry."""
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
        for form, lemma in _clean_base(_layer_entries(fill_path)).items():
            merged.setdefault(form, lemma)
        LOGGER.info("%s: fill layer applied -> %s entries", langcode, len(merged))
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
    chars. Deliberately NOT clean_wordlist.canonicalize: that also folds curly
    quotes, which runtime lookups keep, so folding here would silently drop
    reachable keys (e.g. an apostrophe form like uk "м’ясо") and reviewed
    override forms."""
    return normalize_token(key) == key and not check_field(key)


def _reachable_key(key: str) -> bool:
    """Stricter invariant for MACHINE sources (base wordlist, Wikidata fill):
    additionally no space or punctuation a tokenizer never yields as one token.
    Reviewed overrides are exempt -- they carry deliberate elisions (ro "de-")."""
    return _valid_key(key) and " " not in key and not FIELD_PUNCT.search(key)


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
        value.startswith("-")
        or value.endswith("-")
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
    # an absolute listpath (as tests pass) discards the training-dir prefix
    # per pathlib join semantics.
    source = _read_dict(Path(__file__).parent / listpath / f"{langcode}.txt", langcode)
    if base == "merged":
        source.update(_clean_base(_shipped_str_dict(langcode)))
    return source


def _build_dictionary(
    langcode: str = "en",
    listpath: str = "lists",
    filepath: str | None = None,
    in_place: bool = False,
    base: str = "fresh",
) -> None:
    if base not in BASE_MODES:
        raise ValueError(f"unknown base mode {base!r}, expected one of {BASE_MODES}")
    mydict = _scrub(_apply_layers(_base_source(base, langcode, listpath), langcode))
    if filepath is None:
        # in_place overwrites the shipped data the runtime loads (read at call
        # time so a test's DATA_FOLDER monkeypatch is honored); else training/output/
        if in_place:
            directory = dictionary_factory.DATA_FOLDER
        else:
            directory = Path(__file__).parent / "output"
            directory.mkdir(parents=True, exist_ok=True)
        filepath = str(directory / f"{langcode}.plzma")
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
