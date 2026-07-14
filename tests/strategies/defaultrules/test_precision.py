"""Enforcement harness for the default rules: every rule must stay high-precision
against the shipped dictionaries (lemma-first: the output must BE the dict
lemma), be idempotent, and not overlap. _LEGACY_REAL_WORD_LANGS (eo only)
keeps the older any-dictionary-entry tolerance.
"""

import ast
import importlib
import inspect
import re
import textwrap

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

# Bespoke branches outside DEFAULT_RULES the prefilter must also cover, else
# their firings escape the gate (apply_ru folds a final "ё" before the table).
_EXTRA_MATCH_SURFACE = {"ru": "ё$"}


def _is_pure_wrapper(fn) -> bool:
    """True iff the fn's whole body is one `return apply_rules(..DEFAULT_RULES..)`,
    which fires only where the prefilter matches -- so its skips need no check.
    Structural, so a bespoke branch is detected even before it's registered in
    _EXTRA_MATCH_SURFACE (a single such return can't itself be bespoke)."""
    fn_def = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    assert isinstance(fn_def, ast.FunctionDef)
    body = fn_def.body[1:] if ast.get_docstring(fn_def) else fn_def.body
    return (
        len(body) == 1
        and isinstance(body[0], ast.Return)
        and isinstance(body[0].value, ast.Call)
        and getattr(body[0].value.func, "id", None) == "apply_rules"
        and any(getattr(a, "id", None) == "DEFAULT_RULES" for a in body[0].value.args)
    )


@pytest.mark.parametrize("lang", RULE_LANGS)
def test_rule_quality(lang: str) -> None:
    """Single full-dictionary pass: aggregate precision, per-cell precision, and
    idempotence for one language's rules."""
    d = FACTORY.get_dictionary(lang)
    fn = RULE_FUNCTIONS[lang]
    mod = _rules_module(lang)
    rules = mod.DEFAULT_RULES if mod is not None else None
    branches = {p: pattern_alts(p) for p in rules} if rules is not None else {}
    ordered = list(rules.items()) if rules is not None else []
    # Skip entries no rule can match (guaranteed fn None). The shipped rule
    # shapes reduce to literal suffixes (pattern_alts), so a hash probe replaces
    # the union-regex scan (~5x on fi); shapes pattern_alts lumps and bespoke
    # match surfaces keep a regex fallback. A suffix hit also names its rule,
    # which narrows cell attribution to the few candidate patterns below.
    suffix_rule: dict[str, int] = {}
    lumped: list[int] = []
    for i, (pattern, _repl) in enumerate(ordered):
        alts = branches[pattern]
        # lumped: pattern_alts fell back to the pattern itself, or an alt is a
        # regex fragment, not a literal suffix (eo's merged stem-class shapes)
        if alts == [pattern.pattern] or any(re.escape(a) != a for a in alts):
            lumped.append(i)
        else:
            for alt in alts:
                suffix_rule[alt] = i  # unique: see test_no_alternation_overlap
    lumped_set = frozenset(lumped)  # constant candidate rules for attribution
    # probe only suffix lengths that can end in the token's final character
    lens_by_last: dict[str, list[int]] = {}
    for alt in suffix_rule:
        lens = lens_by_last.setdefault(alt[-1], [])
        if len(alt) not in lens:
            lens.append(len(alt))
    fallback_alts = [f"(?:{ordered[i][0].pattern})" for i in lumped]
    if (extra := _EXTRA_MATCH_SURFACE.get(lang)) is not None:
        fallback_alts.append(f"(?:{extra})")
    fallback = re.compile("|".join(fallback_alts)) if fallback_alts else None
    legacy = lang in _LEGACY_REAL_WORD_LANGS
    fold = lang in _ACCENT_FOLD_LANGS
    # A skip must never be resolvable by fn, else its output escapes measurement.
    # Only a bespoke branch can do that, so re-run fn on skips (inline, no list)
    # for those langs only -- pure wrappers are safe by construction.
    verify_skips = not _is_pure_wrapper(fn)
    fired = ok = 0
    cells: dict[tuple[str, str], list[int]] = {}
    escaped: list[str] = []
    hits: list[int] = []
    for f, gold in d.items():
        if rules is not None:
            hits = [
                suffix_rule[sfx]
                for L in lens_by_last.get(f[-1:], ())
                if len(f) >= L and (sfx := f[-L:]) in suffix_rule
            ]
            if not hits and (fallback is None or fallback.search(f) is None):
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
        # dict entry (the pipeline tries dictionary lookup before rules)
        if p != f and d.get(p) is None:
            p2 = fn(p)
            assert p2 is None or p2 == p, f"{lang}: not idempotent: {f} -> {p} -> {p2}"
        # attribute to the firing cell (data-driven languages only): first
        # candidate rule that rewrites f, in table order (= apply_rules order)
        if rules is not None:
            for i in sorted(lumped_set.union(hits)):
                pattern, repl = ordered[i]
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

    assert not escaped, (
        f"{lang}: prefilter skipped entries fn resolves ({escaped[:5]}); a "
        f"bespoke branch fires off-table -- add its surface to _EXTRA_MATCH_SURFACE"
    )

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
