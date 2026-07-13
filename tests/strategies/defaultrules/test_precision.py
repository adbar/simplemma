"""Enforcement harness for the default rules: every rule must stay high-precision
against the shipped dictionaries (lemma-first: the output must BE the dict
lemma), be idempotent, and not overlap. _LEGACY_REAL_WORD_LANGS (eo only)
keeps the older any-dictionary-entry tolerance.
"""

import importlib
import re

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
# smallest support at which one stray dictionary artifact still passes the bar
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
    # Skip entries no rule can match (guaranteed fn None): one combined regex
    # rejects the ~80% non-matching without fn's full per-pattern scan.
    prefilter = (
        re.compile("|".join(f"(?:{p.pattern})" for p in rules)) if rules else None
    )
    legacy = lang in _LEGACY_REAL_WORD_LANGS
    fold = lang in _ACCENT_FOLD_LANGS
    fired = ok = 0
    cells: dict[tuple[str, str], list[int]] = {}
    for f, gold in d.items():
        if prefilter is not None and prefilter.search(f) is None:
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
        # dict entry (the pipeline tries dictionary lookup before rules)
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
    """No suffix in two rules, and an earlier rule's shorter suffix that
    intercepts a later rule's longer one must produce the same output."""
    mod = _rules_module(lang)
    assert mod is not None
    rules = mod.DEFAULT_RULES
    alts = [
        (i, a, t) for i, (p, t) in enumerate(rules.items()) for a in pattern_alts(p)
    ]
    seen: dict[str, str] = {}
    for _, alt, repl in alts:
        assert alt not in seen, (
            f"{lang}: {alt!r} in two rules (->{seen[alt]} and ->{repl})"
        )
        seen[alt] = repl
    for j, long, t_long in alts:
        for i, short, t_short in alts:
            if i < j and long.endswith(short) and long != short:
                got = long[: len(long) - len(short)] + t_short
                assert got == t_long, (
                    f"{lang}: -{short}->-{t_short} shadows -{long}->-{t_long} "
                    f"(produces {got!r})"
                )
