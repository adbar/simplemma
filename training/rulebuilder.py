"""
Mining/analysis tool for `simplemma/strategies/defaultrules/` candidate rules.

Recipe: `mine()` finds candidate cells -> `trim_by_mass()` drops the
low-frequency tail -> `refine()` builds rules and iterates dropping any cell
that is imprecise or (once combined with the others) under-supported ->
`subsume()` removes alternatives whose own group already produces them via a
more general alternative -> `evaluate()` for the final human-readable report
-> `render_rules_dict()` emits DEFAULT_RULES source (write it directly rather
than hand-copying a printout, which can silently reorder first-match
priority). Not a one-command generator: every language needs real judgment
calls (stoplists, structural guards) on top of this.

`score_cells()` is the one first-match scoring pass everything else is built
from -- `refine()`'s loop and `evaluate()`'s final report both call it rather
than each rolling their own dictionary sweep.
"""

import functools
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable

from simplemma.strategies.dictionaries.dictionary_factory import (
    DefaultDictionaryFactory,
)

Cells = dict[tuple[str, str], int]
Rules = dict[re.Pattern[str], str]

FACTORY = DefaultDictionaryFactory()
MIN_LEN_DEFAULT = 6
SUPPORT_MIN_DEFAULT = 100
PREC_MIN_DEFAULT = 99.0


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
    )


def output_is_lemma(out: str, gold: str) -> bool:
    """Lemma-first predicate (2026-07 policy): a rule output is correct only if
    it IS the gold lemma. Accent-insensitive because some dictionaries carry
    stress marks on lemmas that surface forms lack (uk)."""
    return out == gold or _strip_accents(out) == _strip_accents(gold)


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


_MERGED_SHAPE = re.compile(r"\(([^()?][^()]*)\)\(\?:([^()]*)\)\$")
_FLAT_SHAPE = re.compile(r"\(\?:([^()]*)\)\$")
_STEM_FLOOR_SHAPE = re.compile(r"\(\.\{\d+,\}\)([^()|]+)\$")
_LITERAL_SHAPE = re.compile(r"[^()\[\]{}|?*+.\\]+\$")


@functools.cache
def pattern_alts(pattern: re.Pattern[str]) -> list[str]:
    """Literal suffixes a rule pattern can match. Handles the shipped shapes --
    flat `(?:a|b)$`, merged stem-class `(p|q)(?:a|b)$`, stem-floor `(.{N,})a$`,
    bare literal `a$` -- and falls back to the whole pattern string otherwise,
    so attribution lumps rather than crashes."""
    s = pattern.pattern
    if merged := _MERGED_SHAPE.fullmatch(s):
        prefixes, endings = merged.group(1).split("|"), merged.group(2).split("|")
        return [p + e for p in prefixes for e in endings]
    if flat := _FLAT_SHAPE.fullmatch(s):
        return flat.group(1).split("|")
    if floor := _STEM_FLOOR_SHAPE.fullmatch(s):
        return [floor.group(1)]
    if _LITERAL_SHAPE.fullmatch(s):
        return [s[:-1]]
    return [s]


def _first_match(token: str, rules: Rules) -> tuple[str, str, str] | None:
    """Like `apply_rules`, but also returns the matched alternative and target."""
    for pattern, repl in rules.items():
        out = pattern.sub(repl, token)
        if out != token:
            alt = max(
                (a for a in pattern_alts(pattern) if token.endswith(a)),
                key=len,
                default=pattern.pattern,
            )
            return out, alt, repl
    return None


def mine(
    lang: str,
    min_len: int = MIN_LEN_DEFAULT,
    support_min: int = SUPPORT_MIN_DEFAULT,
    prec_min: float = PREC_MIN_DEFAULT,
    caps_guard: bool = True,
) -> tuple[Cells, dict[str, str]]:
    "Mine suffix->replacement cells, each individually >=prec_min precise."
    d = dict(FACTORY.get_dictionary(lang))
    candidates: Counter[tuple[str, str]] = Counter()
    for f, lemma in d.items():
        if f == lemma or len(f) < min_len or (caps_guard and f[:1].isupper()):
            continue
        cp = _common_prefix_len(f, lemma)
        if cp < 2 or len(f) - cp > 7 or len(lemma) - cp > 7:
            continue
        for ext in range(4):  # extend leftward through the shared stem
            start = cp - ext
            if start < 2 or len(f) - start > 8:
                continue
            candidates[(f[start:], lemma[start:])] += 1
    kept_candidates = {k for k, v in candidates.items() if v >= support_min and k[0]}

    by_len: dict[int, dict[str, list[str]]] = defaultdict(dict)
    for s_from, s_to in kept_candidates:
        by_len[len(s_from)].setdefault(s_from, []).append(s_to)
    lengths = sorted(by_len)

    stats: dict[tuple[str, str], list[int]] = {}
    for f, lemma in d.items():
        if len(f) < min_len or (caps_guard and f[:1].isupper()):
            continue
        for length in lengths:
            # no stem-length floor: matches apply_rules, which has none either
            if length >= len(f):
                break
            suffix = f[-length:]
            for s_to in by_len[length].get(suffix, ()):
                out = f[:-length] + s_to
                st = stats.setdefault((suffix, s_to), [0, 0])
                st[0] += 1
                st[1] += output_is_lemma(out, lemma)

    cells = {
        (sf, st): n
        for (sf, st), (n, ok) in stats.items()
        if n >= support_min and 100 * ok / n >= prec_min
    }
    return cells, d


def group_by_target(cells: Cells) -> dict[str, list[str]]:
    by_target: dict[str, list[str]] = defaultdict(list)
    for sf, st in cells:
        by_target[st].append(sf)
    return dict(by_target)


def build_rules(
    cells: Cells,
    exclude_suffixes: Iterable[str] = (),
    exclude_targets: Iterable[str] = (),
) -> Rules:
    """One compiled regex per target, longest alternative first (else a short
    alt can shadow a longer one) -- confirm with `evaluate()` on the combined set."""
    exclude_suffixes = set(exclude_suffixes)
    exclude_targets = set(exclude_targets)
    rules: Rules = {}
    for target, suffixes in sorted(
        group_by_target(cells).items(),
        key=lambda kv: (
            -max(len(s) for s in kv[1]),
            -sum(cells[(s, kv[0])] for s in kv[1]),
        ),
    ):
        if target in exclude_targets:
            continue
        kept = sorted(
            (s for s in suffixes if s not in exclude_suffixes), key=len, reverse=True
        )
        if kept:
            rules[re.compile(r"(?:" + "|".join(kept) + r")$")] = target
    return rules


def _make_apply_fn(
    rules: Rules,
    min_len: int,
    caps_guard: bool,
    extra_guard: Callable[[str], bool] | None,
) -> Callable[[str], tuple[str, str, str] | None]:
    def apply_fn(token: str) -> tuple[str, str, str] | None:
        if len(token) < min_len or (caps_guard and token[0].isupper()):
            return None
        if extra_guard is not None and extra_guard(token):
            return None
        return _first_match(token, rules)

    return apply_fn


def score_cells(
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
    collect_nonword: bool = False,
) -> tuple[dict[tuple[str, str], list[int]], list[tuple[str, str, str]]]:
    """One first-match pass over `dictionary`: per-(alt, target) [fired, ok]
    counts, the shared primitive `refine()`'s loop and `evaluate()`'s report
    both build on. `ok` uses `output_is_lemma` -- lemma-first policy, 2026-07.

    When `collect_nonword`, also returns every (form, output, gold) firing
    whose output is not itself a dictionary entry -- the only candidates for
    idempotence chains and precision-failure samples, since the real pipeline
    tries dictionary lookup before rules and would never re-fire a rule on a
    dict-entry output."""
    apply_fn = _make_apply_fn(rules, min_len, caps_guard, extra_guard)
    cell_stats: dict[tuple[str, str], list[int]] = {}
    nonword: list[tuple[str, str, str]] = []
    for f, lemma in dictionary.items():
        match = apply_fn(f)
        if match is None:
            continue
        p, alt, repl = match
        good = output_is_lemma(p, lemma)
        cell = cell_stats.setdefault((alt, repl), [0, 0])
        cell[0] += 1
        cell[1] += good
        if collect_nonword and p != f and dictionary.get(p) is None:
            nonword.append((f, p, lemma))
    return cell_stats, nonword


def refine(
    cells: Cells,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
    prec_min: float = PREC_MIN_DEFAULT,
    support_min: int = SUPPORT_MIN_DEFAULT,
    max_iters: int = 8,
) -> Rules:
    """Batch drop-bad-cells loop: build rules from `cells`, drop every cell
    that is either imprecise (<prec_min) or -- once combined with the rest --
    under-supported (<support_min combined firings, though each cell cleared
    that bar independently at mine time), repeat until stable. The
    under-support drop matters because a cell that mine() validated in
    isolation can be starved by an earlier, more general cell intercepting
    most of its tokens once every cell is combined -- and an under-supported
    cell's precision is not a reliable signal (one stray dictionary entry can
    swing it), so it must not be left to fire ungated in the shipped rules."""
    for _ in range(max_iters):
        rules = build_rules(cells)
        cell_stats, _ = score_cells(rules, dictionary, min_len, caps_guard, extra_guard)
        bad = {
            cell
            for cell, (n, ok) in cell_stats.items()
            if n < support_min or 100 * ok / n < prec_min
        }
        bad |= {cell for cell in cells if cell_stats.get(cell, [0])[0] < support_min}
        if not bad:
            return rules
        cells = {cell: n for cell, n in cells.items() if cell not in bad}
    return rules


def subsume(
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
) -> Rules:
    """Drop alternatives that are provably redundant: an earlier group already
    intercepts them, or a later group produces the identical output for them
    (a shorter alt whose replacement is itself a suffix of a longer alt's
    target, e.g. ca's `lades->lada` restating `ades->ada`). `mine()`'s
    leftward stem extension mass-produces these. Verification is scoped, not
    sampled: removing alternative `a` can only change first-match for tokens
    ending in `a`, so checking exactly those tokens is a complete proof of
    output-equivalence, not a heuristic."""
    groups = list(rules.items())
    alts = [(i, a, t) for i, (p, t) in enumerate(groups) for a in pattern_alts(p)]
    removable: set[tuple[int, str]] = set()
    for i, a, t in alts:
        for j, a2, t2 in alts:
            if (i, a) == (j, a2) or not a.endswith(a2) or a == a2:
                continue
            if j < i or a[: len(a) - len(a2)] + t2 == t:
                removable.add((i, a))
                break
    if not removable:
        return rules
    new_rules: Rules = {}
    for i, (pattern, target) in enumerate(groups):
        kept = [a for a in pattern_alts(pattern) if (i, a) not in removable]
        if kept:
            kept = sorted(kept, key=len, reverse=True)
            new_rules[re.compile(r"(?:" + "|".join(kept) + r")$")] = target

    apply_fn = _make_apply_fn(rules, min_len, caps_guard, extra_guard)
    new_apply_fn = _make_apply_fn(new_rules, min_len, caps_guard, extra_guard)
    removed_suffixes = tuple({a for _, a in removable})
    for f in dictionary:
        if not f.endswith(removed_suffixes):
            continue
        before, after = apply_fn(f), new_apply_fn(f)
        before_out = before[0] if before is not None else None
        after_out = after[0] if after is not None else None
        assert before_out == after_out, (
            f"subsume changed output for {f!r}: {before_out!r} -> {after_out!r}"
        )
    return new_rules


def evaluate(
    lang: str,
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
    verbose: bool = True,
) -> dict[str, object]:
    """Precision, idempotence, and coverage of `rules` over the full
    dictionary -- the final human-readable report, built on `score_cells()`.
    Idempotence is skipped when the output is itself a dict entry: the real
    pipeline tries dictionary lookup first, so a rule never re-fires on it."""
    apply_fn = _make_apply_fn(rules, min_len, caps_guard, extra_guard)
    cell_stats, nonword = score_cells(
        rules, dictionary, min_len, caps_guard, extra_guard, collect_nonword=True
    )
    fired = sum(n for n, _ in cell_stats.values())
    ok = sum(ok2 for _, ok2 in cell_stats.values())

    chains = 0
    bad: list[tuple[str, str, str]] = []
    chain_ex: list[tuple[str, str, str, str]] = []
    for f, p, lemma in nonword:
        if not output_is_lemma(p, lemma) and len(bad) < 15:
            bad.append((f, p, lemma))
        match2 = apply_fn(p)
        if match2 is not None and match2[0] != p:
            chains += 1
            if len(chain_ex) < 15:
                chain_ex.append((f, p, match2[0], lemma))

    prec = 100 * ok / fired if fired else 0.0
    coverage = 100 * fired / len(dictionary)
    worst = sorted(
        (
            (100 * ok2 / n, n, alt, repl)
            for (alt, repl), (n, ok2) in cell_stats.items()
            if n >= SUPPORT_MIN_DEFAULT
        ),
        key=lambda row: row[0],
    )
    if verbose:
        print(
            f"{lang}: groups={len(rules)} fired={fired} prec={prec:.2f}% "
            f"chains={chains} coverage={coverage:.2f}%"
        )
        print("  worst cells (n>=100):")
        for cell_prec, n, alt, repl in worst[:15]:
            tag = "<99!" if cell_prec < 99.0 else "ok"
            print(f"    {tag} {cell_prec:5.1f}% n={n:5d} -{alt}->-{repl}")
        if bad:
            print("  precision failures (sample):", bad[:8])
        if chain_ex:
            print("  idempotence chains (sample):")
            for f, p, p2, lemma in chain_ex:
                print(f"    {f} -> {p} -> {p2}  (gold {lemma})")
    return {
        "fired": fired,
        "prec": prec,
        "chains": chains,
        "coverage": coverage,
        "worst": worst,
        "bad": bad,
        "chain_ex": chain_ex,
    }


def trim_by_mass(cells: Cells, share: float = 0.90) -> Cells:
    """Keep the highest-firing cells covering `share` of total firing mass,
    dropping the long low-frequency tail. Safe by construction: only turns
    fired->unfired, never changes an output."""
    total = sum(cells.values())
    threshold = share * total
    kept: Cells = {}
    running = 0
    for cell, n in sorted(cells.items(), key=lambda kv: -kv[1]):
        if running >= threshold:
            break
        kept[cell] = n
        running += n
    return kept


def complexity_report(langs: Iterable[str]) -> None:
    "Groups / alternatives / stoplist size per rule language -- the lean-rules budget check."
    import importlib

    print(f"{'lang':4} {'groups':>7} {'alts':>6} {'stoplist':>9}")
    for lang in sorted(langs):
        modname = "is_" if lang == "is" else lang
        mod = importlib.import_module(f"simplemma.strategies.defaultrules.{modname}")
        if not hasattr(mod, "DEFAULT_RULES"):
            print(f"{lang:4} {'bespoke':>7}")
            continue
        n_alts = sum(len(pattern_alts(p)) for p in mod.DEFAULT_RULES)
        n_stop = len(getattr(mod, "_EXCLUDED", ()))
        print(f"{lang:4} {len(mod.DEFAULT_RULES):7d} {n_alts:6d} {n_stop:9d}")


def render_rules_dict(rules: Rules, indent: str = "    ") -> str:
    "Render `rules` as Python source for a module's DEFAULT_RULES, in order."
    return "\n".join(
        f'{indent}re.compile(r"{pattern.pattern}"): r"{target}",'
        for pattern, target in rules.items()
    )


def print_groups(cells: Cells, top_n_per_target: int | None = None) -> None:
    "Print mined cells grouped by target, largest group first."
    by_target = group_by_target(cells)
    for target, suffixes in sorted(
        by_target.items(), key=lambda kv: -sum(cells[(s, kv[0])] for s in kv[1])
    ):
        total = sum(cells[(s, target)] for s in suffixes)
        print(f"-> -{target}  (n_total={total}, {len(suffixes)} suffixes)")
        rows = sorted(suffixes, key=lambda s: -cells[(s, target)])
        for s in rows[:top_n_per_target]:
            print(f"    n={cells[(s, target)]:5d}  -{s}")


if __name__ == "__main__":
    for language in sys.argv[1:]:
        mined_cells, mined_dict = mine(language)
        trimmed = trim_by_mass(mined_cells, 0.70)
        rules = refine(trimmed, mined_dict)
        rules = subsume(rules, mined_dict)
        evaluate(language, rules, mined_dict)
        print()
