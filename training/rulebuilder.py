"""Mine candidate suffix rules for `simplemma/strategies/defaultrules/`.

Recipe: mine, trim_by_mass, refine, subsume, evaluate. The output still needs
per-language judgment (stoplists, guards). Built tables carry a stem floor
that most shipped modules lack, so re-validate rather than assume parity.
"""

import os
import re
import sys
from collections import Counter, defaultdict

from simplemma.strategies.defaultrules.generic import SuffixRules
from simplemma.strategies.dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
)
from simplemma.utils import strip_diacritics
from training.build_lang_config import BUILD_NORMALIZATION

Cells = dict[tuple[str, str], int]
Rules = SuffixRules

FACTORY = DEFAULT_DICTIONARY_FACTORY
MIN_LEN_DEFAULT = 6
SUPPORT_MIN_DEFAULT = 100
PREC_MIN_DEFAULT = 99.0
# Mining, scoring and build_rules' min_stem must all agree on this.
MIN_STEM_CHARS = 2


# sl dict keys keep pedagogical tone marks absent from real text.
# Elsewhere accents are real letters, so folding would hide wrong outputs.
_ACCENT_FOLD_LANGS = frozenset({"sl"})


def output_is_lemma(out: str, gold: str, *, fold_accents: bool = False) -> bool:
    """True if `out` is the gold lemma, ignoring accents only with `fold_accents`."""
    if out == gold:
        return True
    return fold_accents and strip_diacritics(out) == strip_diacritics(gold)


# Mined suffixes are plain text, so any of these signals bad input like "etc.".
_META = re.compile(r"[.^$*+?()\[\]{}|\\]")


def cell_alts(rules: Rules) -> list[tuple[str, str]]:
    "(suffix, target) pairs of a table, floor dots stripped."
    return [
        (suffix.lstrip("."), target)
        for target, suffixes in rules.cells.items()
        for suffix in suffixes.split()
    ]


def _guarded(token: str) -> bool:
    "The token guards every table built here carries."
    return len(token) < MIN_LEN_DEFAULT or token[:1].isupper()


def proxy_dictionary(lang: str) -> dict[str, str]:
    """Shipped dict minus build-time alias keys, which keep the original value."""
    d = dict(FACTORY.get_dictionary(lang))
    norm = BUILD_NORMALIZATION.get(lang)
    if norm is None or norm.key_alias is None:
        return d
    alias_born = {}
    for key, value in d.items():
        alias = key.translate(norm.key_alias)
        if alias != key:
            alias_born[alias] = value
    return {f: g for f, g in d.items() if alias_born.get(f) != g}


def mine(
    lang: str,
    support_min: int = SUPPORT_MIN_DEFAULT,
    prec_min: float = PREC_MIN_DEFAULT,
) -> tuple[Cells, dict[str, str]]:
    "Mine suffix->replacement cells, each individually >=prec_min precise."
    fold = lang in _ACCENT_FOLD_LANGS
    d = proxy_dictionary(lang)
    candidates: Counter[tuple[str, str]] = Counter()
    for f, lemma in d.items():
        if f == lemma or _guarded(f):
            continue
        cp = len(os.path.commonprefix((f, lemma)))
        if cp < MIN_STEM_CHARS or len(f) - cp > 7 or len(lemma) - cp > 7:
            continue
        for ext in range(4):
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
        if _guarded(f):
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


def _table(groups: dict[str, list[str]]) -> Rules:
    """Guarded table floored at MIN_STEM_CHARS, from literal suffixes only."""
    for target, suffixes in groups.items():
        for s in (*suffixes, target):
            if _META.search(s):
                raise ValueError(f"non-literal suffix/target {s!r} -> {target!r}")
    return SuffixRules(
        {t: " ".join(sorted(ss, key=len, reverse=True)) for t, ss in groups.items()},
        min_stem=MIN_STEM_CHARS,
        min_len=MIN_LEN_DEFAULT,
        caps=True,
    )


def build_rules(cells: Cells) -> Rules:
    "One cell per target, longest/most-supported first (display order only)."
    by_target: dict[str, list[str]] = defaultdict(list)
    for sf, st in cells:
        by_target[st].append(sf)
    groups = dict(
        sorted(
            by_target.items(),
            key=lambda kv: (
                -max(len(s) for s in kv[1]),
                -sum(cells[(s, kv[0])] for s in kv[1]),
            ),
        )
    )
    return _table(groups)


def _score_cell(
    cell_stats: dict[tuple[str, str], list[int]], alt: str, repl: str, good: bool
) -> None:
    "Update one cell's [fired, ok] counts."
    cell = cell_stats.setdefault((alt, repl), [0, 0])
    cell[0] += 1
    cell[1] += good


def score_cells(
    rules: Rules,
    dictionary: dict[str, str],
    fold_accents: bool = False,
) -> tuple[dict[tuple[str, str], list[int]], list[tuple[str, str, str, str, str]]]:
    """Per-(alt, target) [fired, ok] counts over `dictionary`.

    Also returns firings whose output is not a dictionary entry, since the
    pipeline would look those up before rules."""
    cell_stats: dict[tuple[str, str], list[int]] = {}
    nonword: list[tuple[str, str, str, str, str]] = []
    for f, lemma in dictionary.items():
        p = rules.apply(f)
        if p is None:
            continue
        alt, repl = rules.match(f) or ("", "")
        good = output_is_lemma(p, lemma, fold_accents=fold_accents)
        _score_cell(cell_stats, alt, repl, good)
        if p != f and dictionary.get(p) is None:
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
    prec_min: float = PREC_MIN_DEFAULT,
    support_min: int = SUPPORT_MIN_DEFAULT,
    max_iters: int = 8,
    fold_accents: bool = False,
) -> Rules:
    """Repeatedly drop cells that are imprecise or under-supported once combined.

    Combined, a general cell can starve a specific one of its tokens."""
    for _ in range(max_iters):
        rules = build_rules(cells)
        cell_stats, _ = score_cells(rules, dictionary, fold_accents=fold_accents)
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


def subsume(rules: Rules, dictionary: dict[str, str]) -> Rules:
    """Drop suffixes a shorter one already restates (`lades->lada` vs `ades->ada`).

    Only tokens ending in a removed suffix can change, so checking those proves it."""
    alts = cell_alts(rules)
    target_of = dict(alts)
    # Only the longest remaining suffix fires once `a` is gone.
    removable = set()
    for a, t in alts:
        rest = next((a[k:] for k in range(1, len(a)) if a[k:] in target_of), None)
        if rest is not None and a[: len(a) - len(rest)] + target_of[rest] == t:
            removable.add(a)
    if not removable:
        return rules
    groups = {
        target: [a for a in suffixes.split() if a.lstrip(".") not in removable]
        for target, suffixes in rules.cells.items()
    }
    new_rules = _table({t: ss for t, ss in groups.items() if ss})

    removed_suffixes = tuple(removable)
    for f in dictionary:
        if not f.endswith(removed_suffixes):
            continue
        before, after = rules.apply(f), new_rules.apply(f)
        assert before == after, (
            f"subsume changed output for {f!r}: {before!r} -> {after!r}"
        )
    return new_rules


def evaluate(lang: str, rules: Rules, dictionary: dict[str, str]) -> None:
    """Print precision, idempotence and coverage of `rules` over the dictionary."""
    fold = lang in _ACCENT_FOLD_LANGS
    cell_stats, nonword = score_cells(rules, dictionary, fold_accents=fold)
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
        p2 = rules.apply(p)
        if p2 is not None and p2 != p:
            chains += 1
            if len(chain_ex) < 15:
                chain_ex.append((f, p, p2, lemma))
    # Includes failures outside `nonword`, which have no sample.
    fails = {cell: n - ok2 for cell, (n, ok2) in cell_stats.items() if n > ok2}

    prec = 100 * ok / fired if fired else 0.0
    coverage = 100 * fired / len(dictionary)
    print(
        f"{lang}: cells={len(rules.cells)} fired={fired} prec={prec:.2f}% "
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


def trim_by_mass(cells: Cells, share: float = 0.70) -> Cells:
    """Keep the highest-firing cells covering `share` of total firing mass."""
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
        trimmed = trim_by_mass(mined_cells)
        rules = refine(trimmed, mined_dict, fold_accents=language in _ACCENT_FOLD_LANGS)
        rules = subsume(rules, mined_dict)
        evaluate(language, rules, mined_dict)
        print()
