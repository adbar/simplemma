"""Enforcement harness for the default rules: aggregate precision over the shipped
dict must clear the per-language floor (lemma-first), rule chains must converge
within two steps, and rules must not overlap. _LEGACY_REAL_WORD_LANGS (eo only)
keeps the older any-dictionary-entry tolerance.

Fill-augmented languages get a lowered floor: rules score against v2.0 fill
forms they never serve at runtime (dict-lookup precedes rules), so fill drags
measured precision down with no runtime effect.
"""

import ast
import functools
import importlib
import inspect
import re
import textwrap

import pytest

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries.dictionary_factory import (
    DefaultDictionaryFactory,
)
from training.build_lang_config import BUILD_NORMALIZATION
from training.rulebuilder import _ACCENT_FOLD_LANGS, output_is_lemma, pattern_alts

RULE_LANGS = sorted(
    RULE_FUNCTIONS
)  # every registered language, e.g. de en eo et fi lv nl ru
FACTORY = DefaultDictionaryFactory()


def _rules_module(lang: str):
    """The lang's defaultrules submodule, or None if it's bespoke (no DEFAULT_RULES)."""
    # "is" is a Python keyword and can't be a module name; the file is is_.py.
    modname = "is_" if lang == "is" else lang
    mod = importlib.import_module(f"simplemma.strategies.defaultrules.{modname}")
    return mod if hasattr(mod, "DEFAULT_RULES") else None


# Languages whose rules are a {regex: repl} table are auto-detected here, so a
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
    """True iff fn delegates entirely to apply_rules(..DEFAULT_RULES..):
    either a partial wrapping apply_rules (data-driven languages) or a
    function whose whole body is `return apply_rules(..DEFAULT_RULES..)`.
    Pure wrappers fire only where the prefilter matches, so their skips
    need no verification."""
    from simplemma.strategies.defaultrules.generic import apply_rules

    if isinstance(fn, functools.partial) and fn.func is apply_rules:
        return True
    try:
        src = textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError):
        return False
    fn_def = ast.parse(src).body[0]
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
    """Single full-dictionary pass: aggregate precision (per-language floor) and
    idempotence for one language's rules."""
    d = FACTORY.get_dictionary(lang)
    # BUILD_NORMALIZATION alias keys are entries rules never serve at runtime
    # (dict-lookup precedes rules) whose values keep the ORIGIN spelling
    # (ru е-key -> ё-value), so they'd systematically mismatch any rule
    # output -- drop them from the proxy corpus, like fill (see docstring).
    alias_born: dict[str, str] = {}
    norm = BUILD_NORMALIZATION.get(lang)
    if norm is not None and norm.key_alias is not None:
        for k in d:
            a = k.translate(norm.key_alias)
            if a != k:
                alias_born[a] = d[k]
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
    escaped: list[str] = []
    hits: list[int] = []
    for f, gold in d.items():
        if alias_born.get(f) == gold:
            continue
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
