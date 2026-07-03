"""
Mining/analysis tool for `simplemma/strategies/defaultrules/` candidate rules.

Workflow: `mine(lang)` finds candidate suffix->replacement cells that clear
the harness's precision bar in isolation; `build_rules()` consolidates them
into one regex per target; `evaluate()` checks the FULL combined ruleset
(cells can collide once combined, even if each was safe alone); once clean,
`render_rules_dict()` emits the exact-order source for the module's
DEFAULT_RULES -- write it directly into the file rather than hand-copying a
printout, which can silently reorder first-match priority.

Not a one-command generator: every language shipped so far needed real
judgment calls (which alternatives to whitelist, which closed-class
exceptions to carve out) that these numbers surface but don't resolve.
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
    """All literal suffixes a rule pattern can match: a flat alternation
    `(?:a|b)$`, or a captured stem-class prefix followed by endings,
    `(p|q)(?:a|b)$` (expanded as their product)."""
    s = pattern.pattern
    merged = re.fullmatch(r"\(([^()?][^()]*)\)\(\?:([^()]*)\)\$", s)
    if merged:
        prefixes, endings = merged.group(1).split("|"), merged.group(2).split("|")
        return [p + e for p in prefixes for e in endings]
    return s[3:-2].split("|")  # strip "(?:" and ")$"


def _first_match(token: str, rules: Rules) -> tuple[str, str, str] | None:
    """Like `apply_rules`, but also returns the matched alternative and
    target so callers don't have to re-scan the rules to find out."""
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
            # No stem-length floor beyond a non-empty stem: apply_rules has
            # none either, so a stricter floor here would look safe while
            # mining but diverge from what the real rule does at runtime.
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
    """Consolidate mined cells into one compiled regex per target, ordered
    by longest alternative first (a short alt in a big group can otherwise
    shadow a longer, more specific alt in a smaller one). Not universal --
    some languages need a broad cell checked first instead; confirm with
    `evaluate()` on the combined ruleset."""
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
    """Precision, idempotence, and coverage of `rules` over the full
    dictionary. Idempotence tolerates a rule changing its own output further
    only when that intermediate isn't itself a dictionary entry -- the real
    pipeline always tries a dictionary lookup before rules, so a genuine
    word would never reach the rule a second time (matches
    tests/strategies/defaultrules/test_precision.py)."""

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
