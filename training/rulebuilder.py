"""
Mining/analysis tool for `simplemma/strategies/defaultrules/` candidate rules.

Recipe: `mine()` finds candidate cells -> `trim_by_mass()` drops the
low-frequency tail -> `refine()` builds rules and iterates dropping any cell
that is imprecise or (once combined with the others) under-supported ->
`subsume()` removes alternatives whose own group already produces them via a
more general alternative -> `evaluate()` for the dictionary report.
Not a one-command generator: every language needs real judgment calls
(stoplists, structural guards) on top of this.

`build_rules()` now emits a `(?<=..)` stem floor on every group; modules
shipped before that (all current ones except la) lack it, so a regenerated
module will differ from the checked-in one on whole-word matches --
re-validate rather than assume parity.

`score_cells()` is the one first-match scoring pass everything else is built
from -- `refine()`'s loop and `evaluate()`'s final report both call it rather
than each rolling their own dictionary sweep.
"""

import functools
import os
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable

from simplemma.strategies.dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
)
from simplemma.utils import strip_diacritics

Cells = dict[tuple[str, str], int]
Rules = dict[re.Pattern[str], str]

FACTORY = DEFAULT_DICTIONARY_FACTORY  # shared process-wide cache
MIN_LEN_DEFAULT = 6
SUPPORT_MIN_DEFAULT = 100
PREC_MIN_DEFAULT = 99.0
# stem chars required before a suffix match: mine()'s candidate extraction,
# its scoring pass, and _compile_group()'s `(?<=..)` floor must all agree on
# this, or the builder's stats stop describing what the compiled rule fires on.
MIN_STEM_CHARS = 2


# Languages whose reference data carries a PEDAGOGICAL diacritic that normal
# running text omits, so an exact output==gold test spuriously fails and
# folding is warranted. sl tonal inverted-breve/dot (dẹ̑lati) is verified 0%
# in UD lemmas but present in the dict, AND survives the build-side fold
# (BUILD_NORMALIZATION["sl"] leaves ~34.6k keys with combining marks outside
# its pitch set), so rules still fire on marked keys -> fold still needed.
# uk (vowel-stress acute) and la (macron) USED to be here too, but
# BUILD_NORMALIZATION now folds+drops their marked keys at build time
# (drop_folded_keys), so exact-match already clears their precision floors
# (uk 99.85%>=99.0, la 95.62%>=95.5) -- the fold became a no-op (+0.01pp)
# and was removed. Everything else is scored EXACT -- fi ä/ö (18% of UD
# lemmas), cs/sk long-vowel acute (30%/21%) and es/pt lexical acute are
# STANDARD orthographic letters, so folding them would hide genuine
# wrong-letter outputs (aavikoittää != aavikoittaa, bachnuť != bachnúť) --
# the optimism this set removes. (mk's only U+0301 is inside Ѓ/Ќ, never folded.)
_ACCENT_FOLD_LANGS = frozenset({"sl"})


def output_is_lemma(out: str, gold: str, *, fold_accents: bool = False) -> bool:
    """Lemma-first predicate (2026-07 policy): a rule output is correct only if
    it IS the gold lemma. Exact match by default; `fold_accents` relaxes it to
    ignore combining accents, and must be set ONLY for `_ACCENT_FOLD_LANGS`."""
    if out == gold:
        return True
    return fold_accents and strip_diacritics(out) == strip_diacritics(gold)


_MERGED_SHAPE = re.compile(r"\(([^()?][^()]*)\)\(\?:([^()]*)\)\$")
# flat `(?:a|b)$`, optionally stem-floored `(?<=..)(?:a|b)$`
_FLAT_SHAPE = re.compile(r"(?:\(\?<=\.\.\))?\(\?:([^()]*)\)\$")
_STEM_FLOOR_SHAPE = re.compile(r"\(\.\{\d+,\}\)([^()|]+)\$")
_LITERAL_SHAPE = re.compile(r"[^()\[\]{}|?*+.\\]+\$")

# Regex metacharacters that must never appear in a mined literal suffix -- a
# dictionary word-ending is plain text, so one here means bad input (e.g. an
# abbreviation like "etc.") that would emit an over-matching or invalid pattern.
_META = re.compile(r"[.^$*+?()\[\]{}|\\]")


@functools.cache
def pattern_alts(pattern: re.Pattern[str]) -> list[str]:
    """Literal suffixes a rule pattern can match. Handles the shipped shapes --
    flat/stem-floored `(?:a|b)$` or `(?<=..)(?:a|b)$`, merged stem-class
    `(p|q)(?:a|b)$`, stem-floor `(.{N,})a$`, bare literal `a$` -- and falls back
    to the whole pattern string otherwise, so attribution lumps rather than crashes."""
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
        match = pattern.search(token)
        if match is None:
            continue
        out = pattern.sub(repl, token)
        if out == token:
            continue
        # attribute the alternative the engine matched, not the longest
        # endswith candidate: the (?<=..) floor can backtrack past a long
        # alt and fire a shorter same-target one (Xabitis matches -bitis)
        alt = max(
            (a for a in pattern_alts(pattern) if match.group(0).endswith(a)),
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
    fold = lang in _ACCENT_FOLD_LANGS
    d = dict(FACTORY.get_dictionary(lang))
    candidates: Counter[tuple[str, str]] = Counter()
    for f, lemma in d.items():
        if f == lemma or len(f) < min_len or (caps_guard and f[:1].isupper()):
            continue
        cp = len(os.path.commonprefix((f, lemma)))
        if cp < MIN_STEM_CHARS or len(f) - cp > 7 or len(lemma) - cp > 7:
            continue
        for ext in range(4):  # extend leftward through the shared stem
            start = cp - ext
            if start < MIN_STEM_CHARS or len(f) - start > 8:
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
            if length > len(f) - MIN_STEM_CHARS:
                break
            suffix = f[-length:]
            for s_to in by_len[length].get(suffix, ()):
                out = f[:-length] + s_to
                st = stats.setdefault((suffix, s_to), [0, 0])
                st[0] += 1
                st[1] += output_is_lemma(out, lemma, fold_accents=fold)

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


def _compile_group(suffixes: list[str], target: str) -> re.Pattern[str]:
    """Compile one target's alternation. The `(?<=..)` stem floor mirrors
    mine()'s candidate support and scoring pass (both gated on MIN_STEM_CHARS)
    so a whole-word match can't strip to a bare target (e.g. la `abimus`->`o`)
    and compiled rules fire on exactly the firings mine() scored. Suffixes
    must be metacharacter-free (they are dictionary word-endings) so the
    alternation stays literal."""
    for s in (*suffixes, target):
        if _META.search(s):
            raise ValueError(f"non-literal suffix/target {s!r} for target {target!r}")
    kept = sorted(suffixes, key=len, reverse=True)
    floor = f"(?<={'.' * MIN_STEM_CHARS})"
    return re.compile(floor + r"(?:" + "|".join(kept) + r")$")


def build_rules(cells: Cells) -> Rules:
    """One compiled regex per target, longest alternative first (else a short
    alt can shadow a longer one) -- confirm with `evaluate()` on the combined set."""
    rules: Rules = {}
    for target, suffixes in sorted(
        group_by_target(cells).items(),
        key=lambda kv: (
            -max(len(s) for s in kv[1]),
            -sum(cells[(s, kv[0])] for s in kv[1]),
        ),
    ):
        rules[_compile_group(suffixes, target)] = target
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


def _score_cell(
    cell_stats: dict[tuple[str, str], list[int]], alt: str, repl: str, good: bool
) -> None:
    "Update one cell's [fired, ok] counts -- the bookkeeping score_cells() uses."
    cell = cell_stats.setdefault((alt, repl), [0, 0])
    cell[0] += 1
    cell[1] += good


def score_cells(
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
    collect_nonword: bool = False,
    fold_accents: bool = False,
) -> tuple[dict[tuple[str, str], list[int]], list[tuple[str, str, str, str, str]]]:
    """One first-match pass over `dictionary`: per-(alt, target) [fired, ok]
    counts, the shared primitive `refine()`'s loop and `evaluate()`'s report
    both build on. `ok` uses `output_is_lemma` -- lemma-first policy, 2026-07.

    When `collect_nonword`, also returns every (form, output, gold, alt, target)
    firing whose output is not itself a dictionary entry -- the only candidates
    for idempotence chains and precision-failure samples, since the real
    pipeline tries dictionary lookup before rules and would never re-fire a
    rule on a dict-entry output."""
    apply_fn = _make_apply_fn(rules, min_len, caps_guard, extra_guard)
    cell_stats: dict[tuple[str, str], list[int]] = {}
    nonword: list[tuple[str, str, str, str, str]] = []
    for f, lemma in dictionary.items():
        match = apply_fn(f)
        if match is None:
            continue
        p, alt, repl = match
        good = output_is_lemma(p, lemma, fold_accents=fold_accents)
        _score_cell(cell_stats, alt, repl, good)
        if collect_nonword and p != f and dictionary.get(p) is None:
            nonword.append((f, p, lemma, alt, repl))
    return cell_stats, nonword


def _worst_cells(
    cell_stats: dict[tuple[str, str], list[int]], min_n: int
) -> list[tuple[float, int, str, str]]:
    "Per-cell (prec, n, alt, target) rows, worst first, for cells with n >= min_n."
    return sorted(
        (
            (100 * ok / n, n, alt, repl)
            for (alt, repl), (n, ok) in cell_stats.items()
            if n >= min_n
        ),
        key=lambda row: row[0],
    )


def refine(
    cells: Cells,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
    prec_min: float = PREC_MIN_DEFAULT,
    support_min: int = SUPPORT_MIN_DEFAULT,
    max_iters: int = 8,
    fold_accents: bool = False,
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
        cell_stats, _ = score_cells(
            rules,
            dictionary,
            min_len,
            caps_guard,
            extra_guard,
            fold_accents=fold_accents,
        )
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
    by_alt: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for j, a2, t2 in alts:
        by_alt[a2].append((j, t2))
    # `a` is redundant iff one of its proper suffixes is itself an alternative
    # that either intercepts it earlier (j < i) or rewrites to the same output.
    removable = {
        (i, a)
        for i, a, t in alts
        for k in range(1, len(a))
        for j, t2 in by_alt.get(a[k:], ())
        if j < i or a[:k] + t2 == t
    }
    if not removable:
        return rules
    new_rules: Rules = {}
    for i, (pattern, target) in enumerate(groups):
        kept = [a for a in pattern_alts(pattern) if (i, a) not in removable]
        if kept:
            new_rules[_compile_group(kept, target)] = target

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
) -> None:
    """Precision, idempotence, and coverage of `rules` over the full
    dictionary -- the final human-readable report, built on `score_cells()`.
    Idempotence is skipped when the output is itself a dict entry: the real
    pipeline tries dictionary lookup first, so a rule never re-fires on it.
    Failures are grouped per cell: a small coherent word list is a finite
    lexical collision (stoplist it in the module's _EXCLUDED), a large or
    scattered one means the cell itself needs narrowing or dropping."""
    fold = lang in _ACCENT_FOLD_LANGS
    apply_fn = _make_apply_fn(rules, min_len, caps_guard, extra_guard)
    cell_stats, nonword = score_cells(
        rules,
        dictionary,
        min_len,
        caps_guard,
        extra_guard,
        collect_nonword=True,
        fold_accents=fold,
    )
    fired = sum(n for n, _ in cell_stats.values())
    ok = sum(ok2 for _, ok2 in cell_stats.values())

    chains = 0
    bad: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    chain_ex: list[tuple[str, str, str, str]] = []
    for f, p, lemma, alt, repl in nonword:
        if (
            not output_is_lemma(p, lemma, fold_accents=fold)
            and len(bad[(alt, repl)]) < 5
        ):
            bad[(alt, repl)].append((f, p, lemma))
        match2 = apply_fn(p)
        if match2 is not None and match2[0] != p:
            chains += 1
            if len(chain_ex) < 15:
                chain_ex.append((f, p, match2[0], lemma))
    # exact per-cell failure counts (n - ok covers even failures whose wrong
    # output is a dict entry, which never enter `nonword` and have no sample)
    fails = {cell: n - ok2 for cell, (n, ok2) in cell_stats.items() if n > ok2}

    prec = 100 * ok / fired if fired else 0.0
    coverage = 100 * fired / len(dictionary)
    print(
        f"{lang}: groups={len(rules)} fired={fired} prec={prec:.2f}% "
        f"chains={chains} coverage={coverage:.2f}%"
    )
    print("  worst cells (n>=100):")
    for cell_prec, n, alt, repl in _worst_cells(cell_stats, SUPPORT_MIN_DEFAULT)[:15]:
        tag = "<99!" if cell_prec < 99.0 else "ok"
        print(f"    {tag} {cell_prec:5.1f}% n={n:5d} -{alt}->-{repl}")
    if fails:
        print("  precision failures by cell (few coherent words -> stoplist;")
        print("  many/scattered -> narrow or drop the cell):")
        for cell, n_bad in sorted(fails.items(), key=lambda kv: -kv[1]):
            alt, repl = cell
            print(f"    {n_bad:4d}  -{alt}->-{repl}  {bad.get(cell, [])}")
    if chain_ex:
        print("  idempotence chains (sample):")
        for f, p, p2, lemma in chain_ex:
            print(f"    {f} -> {p} -> {p2}  (gold {lemma})")


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


if __name__ == "__main__":
    for language in sys.argv[1:]:
        mined_cells, mined_dict = mine(language)
        trimmed = trim_by_mass(mined_cells, 0.70)
        rules = refine(trimmed, mined_dict, fold_accents=language in _ACCENT_FOLD_LANGS)
        rules = subsume(rules, mined_dict)
        evaluate(language, rules, mined_dict)
        print()
