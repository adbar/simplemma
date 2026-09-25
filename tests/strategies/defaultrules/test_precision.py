"""Enforcement harness for the default rules: aggregate precision over the shipped
dict must clear the per-language floor (lemma-first), rule chains must converge
within two steps, and rules must not overlap. _LEGACY_REAL_WORD_LANGS (eo only)
keeps the older any-dictionary-entry tolerance.

Fill-augmented languages get a lowered floor: rules score against v2.0 fill
forms they never serve at runtime (dict-lookup precedes rules), so fill drags
measured precision down with no runtime effect.
"""

import importlib
import re

import pytest

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.defaultrules.generic import SuffixRules
from training.rulebuilder import (
    _ACCENT_FOLD_LANGS,
    FACTORY,
    cell_alts,
    output_is_lemma,
    proxy_dictionary,
)

RULE_LANGS = sorted(
    RULE_FUNCTIONS
)  # every registered language, e.g. de en eo et fi lv nl ru


def _rules_module(lang: str):
    """The lang's defaultrules submodule, or None if it's bespoke (no DEFAULT_RULES)."""
    # "is" is a Python keyword and can't be a module name; the file is is_.py.
    modname = "is_" if lang == "is" else lang
    mod = importlib.import_module(f"simplemma.strategies.defaultrules.{modname}")
    return mod if hasattr(mod, "DEFAULT_RULES") else None


# Languages whose rules are a SuffixRules table are auto-detected here, so a
# newly registered language is gated by the overlap test without editing it.
DATA_DRIVEN = sorted(lang for lang in RULE_LANGS if _rules_module(lang) is not None)

THRESHOLD = 99.0
# Per-language floor override for langs with Wikidata fill in the shipped dict
# (rules score against fill but never serve it at runtime). Value = full-dict
# precision minus ~0.4pp headroom (et 98.38%, la 96.06%; misses are convention
# mismatches, not rule defects -- excluding fill clears THRESHOLD for both).
_AGGREGATE_BASELINE = {"et": 98.0, "la": 95.5}

# Gate still accepts any dictionary-entry output for these (see docstring).
_LEGACY_REAL_WORD_LANGS = frozenset({"eo"})

# Bespoke branches outside DEFAULT_RULES the prefilter must also cover, else
# their firings escape the gate (apply_ru folds a final "ё" before the table).
_EXTRA_MATCH_SURFACE = {"ru": "ё$"}


def _is_pure_wrapper(fn) -> bool:
    """True iff fn is a table's own `apply` (data-driven language): it fires only
    where the table matches, so its skips need no verification."""
    return isinstance(getattr(fn, "__self__", None), SuffixRules)


@pytest.mark.parametrize("lang", RULE_LANGS)
def test_rule_quality(lang: str) -> None:
    """Single full-dictionary pass: aggregate precision (per-language floor) and
    idempotence for one language's rules."""
    d = FACTORY.get_dictionary(lang)
    fn = RULE_FUNCTIONS[lang]
    mod = _rules_module(lang)
    rules = mod.DEFAULT_RULES if mod is not None else None
    # skip entries no cell matches (fn is None there); bespoke surfaces keep a regex
    extra = _EXTRA_MATCH_SURFACE.get(lang)
    fallback = re.compile(extra) if extra is not None else None
    legacy = lang in _LEGACY_REAL_WORD_LANGS
    fold = lang in _ACCENT_FOLD_LANGS
    # A skip must never be resolvable by fn, else its output escapes measurement.
    # Only a bespoke branch can do that, so re-run fn on skips (inline, no list)
    # for those langs only -- pure wrappers are safe by construction.
    verify_skips = not _is_pure_wrapper(fn)
    fired = ok = 0
    escaped: list[str] = []
    for f, gold in proxy_dictionary(lang).items():
        if rules is not None and rules.match(f) is None:
            if fallback is None or fallback.search(f) is None:
                if verify_skips and fn(f) is not None:
                    escaped.append(f)
                continue
        p = fn(f)
        if p is None:
            continue
        fired += 1
        good = output_is_lemma(p, gold, fold_accents=fold) or (
            legacy and d.get(p) is not None
        )
        ok += good
        # idempotence: a produced lemma must be a fixed point unless it is a
        # dict entry (the pipeline tries dictionary lookup before rules). One
        # extra hop is tolerated if the chain terminates there: v2.0 fill forms
        # can surface 2-step chains (la centensimabam -> centensimo -> centensimus).
        if p != f and d.get(p) is None:
            p2 = fn(p)
            if p2 is not None and p2 != p and d.get(p2) is None:
                p3 = fn(p2)
                assert p3 is None or p3 == p2, (
                    f"{lang}: rule chain doesn't converge: {f} -> {p} -> {p2} -> {p3}"
                )

    assert not escaped, (
        f"{lang}: prefilter skipped entries fn resolves ({escaped[:5]}); a "
        f"bespoke branch fires off-table -- add its surface to _EXTRA_MATCH_SURFACE"
    )

    prec = 100 * ok / fired if fired else 100.0
    floor = _AGGREGATE_BASELINE.get(lang, THRESHOLD)
    assert prec >= floor, (
        f"{lang}: aggregate precision {prec:.2f}% over {fired} firings (floor {floor}%)"
    )


@pytest.mark.parametrize("lang", DATA_DRIVEN)
def test_no_suffix_overlap(lang: str) -> None:
    """No suffix in two cells (the table would silently keep the last one)."""
    mod = _rules_module(lang)
    assert mod is not None
    seen: dict[str, str] = {}
    for suffix, target in cell_alts(mod.DEFAULT_RULES):
        assert suffix not in seen, (
            f"{lang}: {suffix!r} in two cells (->{seen[suffix]} and ->{target})"
        )
        seen[suffix] = target
