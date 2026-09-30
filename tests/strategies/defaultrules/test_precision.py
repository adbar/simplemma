"""Default rules gate: precision floor, chain convergence and no suffix overlap."""

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

RULE_LANGS = sorted(RULE_FUNCTIONS)


def _rules_module(lang: str):
    """The lang's defaultrules submodule, or None if it's bespoke (no DEFAULT_RULES)."""
    # "is" is a Python keyword, so the module is is_.py
    modname = "is_" if lang == "is" else lang
    mod = importlib.import_module(f"simplemma.strategies.defaultrules.{modname}")
    return mod if hasattr(mod, "DEFAULT_RULES") else None


DATA_DRIVEN = sorted(lang for lang in RULE_LANGS if _rules_module(lang) is not None)

THRESHOLD = 99.0
# lower floors: rules score against fill entries they never serve at runtime
_AGGREGATE_BASELINE = {"et": 98.0, "la": 95.5}

# any dictionary-entry output still counts as correct for these
_LEGACY_REAL_WORD_LANGS = frozenset({"eo"})

# off-table bespoke branches the prefilter must cover (apply_ru folds a final "ё")
_EXTRA_MATCH_SURFACE = {"ru": "ё$"}


def _is_pure_wrapper(fn) -> bool:
    """True iff fn is a table's own `apply`, which fires only where the table does."""
    return isinstance(getattr(fn, "__self__", None), SuffixRules)


@pytest.mark.parametrize("lang", RULE_LANGS)
def test_rule_quality(lang: str) -> None:
    """Aggregate precision and idempotence in one full-dictionary pass."""
    d = FACTORY.get_dictionary(lang)
    fn = RULE_FUNCTIONS[lang]
    mod = _rules_module(lang)
    rules = mod.DEFAULT_RULES if mod is not None else None
    extra = _EXTRA_MATCH_SURFACE.get(lang)
    fallback = re.compile(extra) if extra is not None else None
    legacy = lang in _LEGACY_REAL_WORD_LANGS
    fold = lang in _ACCENT_FOLD_LANGS
    # only a bespoke branch can resolve a skipped entry, so check skips there
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
        # a non-dict lemma must converge within one extra hop
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
