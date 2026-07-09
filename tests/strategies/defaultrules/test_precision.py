"""Enforcement harness for the default rules: every rule must stay high-precision
against the shipped dictionaries, be idempotent, and not overlap.

The dictionaries are treated as ground truth. Policy (2026-07, lemma-first): a
rule's output counts as correct only when it IS the dictionary lemma (exact,
except the pedagogical-accent fold for _ACCENT_FOLD_LANGS) -- rules exist to
produce lemmas, not other inflected forms; see
training/rulebuilder.output_is_lemma. _LEGACY_REAL_WORD_LANGS keeps
the older tolerance (any dictionary-entry output counts): only Esperanto
remains -- its base cells need a from-scratch rebuild to pass the strict bar.
"""

import importlib

import pytest

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries.dictionary_factory import (
    DefaultDictionaryFactory,
)
from training.rulebuilder import _ACCENT_FOLD_LANGS, output_is_lemma, pattern_alts

RULE_LANGS = sorted(
    RULE_FUNCTIONS
)  # every registered language, e.g. de en eo et fi lv nl pl ru
FACTORY = DefaultDictionaryFactory()


def _rules_module(lang: str):
    """The lang's defaultrules submodule, or None if it's bespoke (no DEFAULT_RULES)."""
    # "is" is a Python keyword and can't be a module name; the file is is_.py.
    modname = "is_" if lang == "is" else lang
    mod = importlib.import_module(f"simplemma.strategies.defaultrules.{modname}")
    return mod if hasattr(mod, "DEFAULT_RULES") else None


# Languages whose rules are a {regex: repl} table are auto-detected here, so a
# newly registered language is gated by the per-cell test without editing it.
DATA_DRIVEN = sorted(lang for lang in RULE_LANGS if _rules_module(lang) is not None)

THRESHOLD = 99.0
# Below this a single idiosyncratic dictionary entry (loanword, pluralia tantum,
# proper-noun artifact) already breaches the threshold, so the cell's precision
# is not a reliable signal; 1/(1 - THRESHOLD/100) is the smallest support at
# which one stray failure still passes. Systematically bad cells fire far more.
MIN_SUPPORT = round(100 / (100 - THRESHOLD))  # 100 at THRESHOLD=99.0

# Gate still accepts any dictionary-entry output for these (see docstring).
_LEGACY_REAL_WORD_LANGS = frozenset({"eo"})


@pytest.mark.parametrize("lang", RULE_LANGS)
def test_rule_quality(lang: str) -> None:
    """Single full-dictionary pass: aggregate precision, per-cell precision, and
    idempotence for one language's rules."""
    d = FACTORY.get_dictionary(lang)
    fn = RULE_FUNCTIONS[lang]
    mod = _rules_module(lang)
    rules = mod.DEFAULT_RULES if mod is not None else None
    branches = {p: pattern_alts(p) for p in rules} if rules is not None else {}
    legacy = lang in _LEGACY_REAL_WORD_LANGS
    fold = lang in _ACCENT_FOLD_LANGS
    fired = ok = 0
    cells: dict[tuple[str, str], list[int]] = {}
    for f, gold in d.items():
        p = fn(f)
        if p is None:
            continue
        fired += 1
        good = output_is_lemma(p, gold, fold_accents=fold) or (
            legacy and d.get(p) is not None
        )
        ok += good
        # idempotence: a produced lemma must be a fixed point, UNLESS it is
        # itself a real dictionary entry -- the real pipeline always tries
        # dictionary lookup before rules, so such a lemma would never reach
        # this rule again.
        if p != f and d.get(p) is None:
            p2 = fn(p)
            assert p2 is None or p2 == p, f"{lang}: not idempotent: {f} -> {p} -> {p2}"
        # attribute to the firing cell (data-driven languages only)
        if rules is not None:
            for pattern, repl in rules.items():
                if pattern.sub(repl, f) != f:
                    alt = max(
                        (a for a in branches[pattern] if f.endswith(a)),
                        key=len,
                        default=pattern.pattern,
                    )
                    s = cells.setdefault((alt, repl), [0, 0])
                    s[0] += 1
                    s[1] += good
                    break

    prec = 100 * ok / fired if fired else 100.0
    assert prec >= THRESHOLD, (
        f"{lang}: aggregate precision {prec:.2f}% over {fired} firings"
    )
    bad = [
        f"-{alt}->-{repl} {100 * ok / n:.1f}% (n={n})"
        for (alt, repl), (n, ok) in cells.items()
        if n >= MIN_SUPPORT and 100 * ok / n < THRESHOLD
    ]
    assert not bad, f"{lang}: rule cells below {THRESHOLD}%: {bad}"


@pytest.mark.parametrize("lang", DATA_DRIVEN)
def test_no_alternation_overlap(lang: str) -> None:
    """A suffix must not appear in two rules (would shadow the later one)."""
    mod = _rules_module(lang)
    assert mod is not None
    rules = mod.DEFAULT_RULES
    seen: dict[str, str] = {}
    for pattern, repl in rules.items():
        for alt in pattern_alts(pattern):
            assert alt not in seen, (
                f"{lang}: {alt!r} in two rules (->{seen[alt]} and ->{repl})"
            )
            seen[alt] = repl
