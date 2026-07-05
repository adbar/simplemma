"""
Mining/analysis tool for `simplemma/strategies/defaultrules/` candidate rules.

Workflow: `mine()` finds candidate cells, `build_rules()` consolidates them,
`evaluate()` checks the combined ruleset (cells can collide once combined),
`render_rules_dict()` emits DEFAULT_RULES source -- write it directly rather
than hand-copying a printout, which can silently reorder first-match priority.
Not a one-command generator: every language needs real judgment calls.
"""

import re
import sys
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


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _alts(pattern: re.Pattern[str]) -> list[str]:
    """Literal suffixes a rule pattern can match: `(?:a|b)$` or `(p|q)(?:a|b)$`."""
    s = pattern.pattern
    merged = re.fullmatch(r"\(([^()?][^()]*)\)\(\?:([^()]*)\)\$", s)
    if merged:
        prefixes, endings = merged.group(1).split("|"), merged.group(2).split("|")
        return [p + e for p in prefixes for e in endings]
    return s[3:-2].split("|")  # strip "(?:" and ")$"


def _first_match(token: str, rules: Rules) -> tuple[str, str, str] | None:
    """Like `apply_rules`, but also returns the matched alternative and target."""
    for pattern, repl in rules.items():
        out = pattern.sub(repl, token)
        if out != token:
            alt = max((a for a in _alts(pattern) if token.endswith(a)), key=len)
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
                st[1] += out == lemma or d.get(out) is not None

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


def evaluate(
    lang: str,
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
    verbose: bool = True,
) -> dict[str, object]:
    """Precision, idempotence, and coverage of `rules` over the full dictionary.
    Idempotence is skipped when the output is itself a dict entry: the real
    pipeline tries dictionary lookup first, so a rule never re-fires on it."""

    def apply_fn(token: str) -> tuple[str, str, str] | None:
        if len(token) < min_len or (caps_guard and token[0].isupper()):
            return None
        if extra_guard is not None and extra_guard(token):
            return None
        return _first_match(token, rules)

    fired = ok = chains = 0
    bad: list[tuple[str, str, str]] = []
    chain_ex: list[tuple[str, str, str, str]] = []
    cell_stats: dict[tuple[str, str], list[int]] = {}
    for f, lemma in dictionary.items():
        match = apply_fn(f)
        if match is None:
            continue
        p, alt, repl = match
        fired += 1
        p_is_word = dictionary.get(p) is not None
        good = p == lemma or p_is_word
        ok += good
        if not good and len(bad) < 15:
            bad.append((f, p, lemma))
        if p != f and not p_is_word:
            match2 = apply_fn(p)
            if match2 is not None and match2[0] != p:
                chains += 1
                if len(chain_ex) < 15:
                    chain_ex.append((f, p, match2[0], lemma))
        cell = cell_stats.setdefault((alt, repl), [0, 0])
        cell[0] += 1
        cell[1] += good

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


def cell_firing_counts(
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
) -> Cells:
    "Per-(alt, target) firing counts of an already-built ruleset -- the input to trim_by_mass."

    def apply_fn(token: str) -> tuple[str, str, str] | None:
        if len(token) < min_len or (caps_guard and token[0].isupper()):
            return None
        if extra_guard is not None and extra_guard(token):
            return None
        return _first_match(token, rules)

    counts: Counter[tuple[str, str]] = Counter()
    for f in dictionary:
        match = apply_fn(f)
        if match is not None:
            _, alt, repl = match
            counts[(alt, repl)] += 1
    return dict(counts)


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


def merge_stem_classes(
    rules: Rules,
    dictionary: dict[str, str],
    min_len: int = MIN_LEN_DEFAULT,
    caps_guard: bool = True,
    extra_guard: Callable[[str], bool] | None = None,
) -> Rules:
    """Merge plain suffix-stripping groups (target is a literal prefix of every
    alternative, e.g. sv's -ig/-lig/-sig) that share an identical ending set,
    at the earliest source group's position. Rejected unless it reproduces
    the exact same output for every dictionary entry -- a merge can silently
    collide with an unrelated group positioned in between (the sv rat|rn lesson)."""
    items = list(rules.items())
    deletion: dict[str, tuple[int, frozenset[str]]] = {}
    for i, (pattern, target) in enumerate(items):
        alts = _alts(pattern)
        if all(a.startswith(target) and len(a) > len(target) for a in alts):
            deletion[target] = (i, frozenset(a[len(target) :] for a in alts))

    by_endings: dict[frozenset[str], list[str]] = defaultdict(list)
    for target, (_, endings) in deletion.items():
        by_endings[endings].append(target)

    def apply_fn(token: str, active: Rules) -> str | None:
        if len(token) < min_len or (caps_guard and token[0].isupper()):
            return None
        if extra_guard is not None and extra_guard(token):
            return None
        for pattern, repl in active.items():
            out = pattern.sub(repl, token)
            if out != token:
                return out
        return None

    result = dict(items)
    for endings, targets in by_endings.items():
        if len(targets) < 2:
            continue
        earliest = min(deletion[t][0] for t in targets)
        anchor_pattern = items[earliest][0]
        stems = sorted(targets, key=len, reverse=True)
        stem_pat = "|".join(re.escape(s) for s in stems)
        end_pat = "|".join(sorted(endings, key=len, reverse=True))
        merged_pattern = re.compile(rf"({stem_pat})(?:{end_pat})$")

        candidate = {
            (merged_pattern if p is anchor_pattern else p): t
            for p, t in result.items()
            if t not in targets or p is anchor_pattern
        }
        candidate[merged_pattern] = r"\1"
        # `result` stands in for the baseline: sound by induction, already verified
        if all(apply_fn(f, candidate) == apply_fn(f, result) for f in dictionary):
            result = candidate
    return result


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
        n_alts = sum(len(_alts(p)) for p in mod.DEFAULT_RULES)
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
        evaluate(language, build_rules(mined_cells), mined_dict)
        print()
