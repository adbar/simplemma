"""
Production-faithful UD evaluation of affix/rules config changes: runs the
full non-greedy pipeline (fresh Lemmatizer per config) and reports accuracy
plus improved/worsened diff counts for a runtime-patched candidate config
against the unpatched baseline.

Config strings accepted by patched() -- both the pre- and post-
fix/simplify_affixes shapes of AFFIX_LANGS are supported (set+LONGER_AFFIXES
vs dict lang->max_affix_len), detected at run time:
  add:<lang>       lang added to AFFIX_LANGS (max_affix_len 2)
  remove:<lang>    lang removed from AFFIX_LANGS
  retune:<lang>N   lang's max_affix_len set to N
  gate:<lang>N     lang's affix ENTRY gate set to N (affix side only)
  gate-affix:N     entry gate set to N for ALL langs
  gate-both:N      entry gate AND greedy-lookup gate set to N, ALL langs
  greedy_exclude:<lang>  lang added to GREEDY_EXCLUDE (post-affix-branch
                   shape only; a no-op question in non-greedy mode)

The decision protocol lives here too (pre-registered, 2026-07-03): a change
is ACCEPTed only if it wins the sign test on the TUNE split (dev) AND the
CONFIRM split (test) agrees -- two independent samples, never one pooled
number -- and no single systematic harm class dominates the worsened set
(run training/diff_audit.py --config before trusting any verdict). Gate
changes additionally need the greedy-mode regression leg (greedy_leg here):
the gate is shared with GreedyDictionaryLookupStrategy by design.

CLI: uv run python -m training.ud_end_to_end <lang> <ud_prefix> <config> [...]
"""

import math
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import simplemma.strategies.affix_decomposition as AD  # noqa: E402
import simplemma.strategies.greedy_dictionary_lookup as GDL  # noqa: E402
from simplemma import Lemmatizer  # noqa: E402
from simplemma.strategies.default import DefaultStrategy  # noqa: E402
from simplemma.strategies.dictionary_lookup import (  # noqa: E402
    DictionaryLookupStrategy,
)
from training.ud_eval import iter_tokens  # noqa: E402

DICT_LOOKUP = DictionaryLookupStrategy()


def iter_eval_tokens(
    prefix: str, splits: tuple[str, ...] = ("test", "dev")
) -> Iterator[tuple[str, str]]:
    "(form, lemma); splits=('dev',)/('test',) for the tune/confirm protocol."
    for form, lemma, _ in iter_tokens(prefix, splits):
        yield form, lemma


def _set_max_affix_len(lang: str, n: int) -> None:
    if isinstance(AD.AFFIX_LANGS, dict):
        AD.AFFIX_LANGS = {**AD.AFFIX_LANGS, lang: n}
    else:  # pre-affix-branch shape: set + LONGER_AFFIXES/LONGAFFIXLEN
        AD.AFFIX_LANGS = set(AD.AFFIX_LANGS) | {lang}
        if n == AD.AFFIXLEN:
            AD.LONGER_AFFIXES = set(AD.LONGER_AFFIXES) - {lang}
        else:
            AD.LONGER_AFFIXES = set(AD.LONGER_AFFIXES) | {lang}
            AD.LONGAFFIXLEN = n


@contextmanager
def patched(config: str) -> Iterator[None]:
    saved: dict[str, Any] = {
        "AFFIX_LANGS": AD.AFFIX_LANGS,
        "greedy_min_length": getattr(AD, "greedy_min_length"),
        "gdl_greedy_min_length": GDL.greedy_min_length,
    }
    for opt in ("LONGER_AFFIXES", "LONGAFFIXLEN", "GREEDY_EXCLUDE"):
        if hasattr(AD, opt):
            saved[opt] = getattr(AD, opt)
    try:
        kind, _, arg = config.partition(":")
        if kind == "add":
            _set_max_affix_len(arg, 2)
        elif kind == "remove":
            if isinstance(AD.AFFIX_LANGS, dict):
                AD.AFFIX_LANGS = {k: v for k, v in AD.AFFIX_LANGS.items() if k != arg}
            else:
                AD.AFFIX_LANGS = set(AD.AFFIX_LANGS) - {arg}
        elif kind == "retune":
            _set_max_affix_len(arg[:-1], int(arg[-1]))
        elif kind == "gate":
            lang, n = arg[:-1], int(arg[-1])
            base_fn = saved["greedy_min_length"]

            def _per_lang(lg: str, _n: int = n, _lang: str = lang) -> int:
                return _n if lg == _lang else int(base_fn(lg))

            setattr(AD, "greedy_min_length", _per_lang)
        elif kind == "gate-affix":
            setattr(AD, "greedy_min_length", lambda lang, _n=int(arg): _n)
        elif kind == "gate-both":
            setattr(AD, "greedy_min_length", lambda lang, _n=int(arg): _n)
            setattr(GDL, "greedy_min_length", lambda lang, _n=int(arg): _n)
        elif kind == "greedy_exclude":
            setattr(AD, "GREEDY_EXCLUDE", getattr(AD, "GREEDY_EXCLUDE") | {arg})
        elif kind != "baseline":
            raise ValueError(config)
        yield
    finally:
        AD.AFFIX_LANGS = saved["AFFIX_LANGS"]
        setattr(AD, "greedy_min_length", saved["greedy_min_length"])
        setattr(GDL, "greedy_min_length", saved["gdl_greedy_min_length"])
        for opt in ("LONGER_AFFIXES", "LONGAFFIXLEN", "GREEDY_EXCLUDE"):
            if opt in saved:
                setattr(AD, opt, saved[opt])


def run(
    lang: str,
    prefix: str,
    config: str,
    splits: tuple[str, ...] = ("test", "dev"),
    greedy: bool = False,
) -> tuple[int, float, int, float]:
    "(tokens, accuracy%, oov_tokens, oov_accuracy%) under `config`."
    with patched(config):
        lemmatizer = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=greedy))
        total = ok = sub_total = sub_ok = 0
        for form, lemma in iter_eval_tokens(prefix, splits):
            candidate = lemmatizer.lemmatize(form, lang=lang)
            good = candidate == lemma
            total += 1
            ok += good
            if (
                form[:1].islower()
                and form.isalpha()
                and DICT_LOOKUP.get_lemma(form, lang) is None
            ):
                sub_total += 1
                sub_ok += good
    return (
        total,
        100 * ok / total if total else 0.0,
        sub_total,
        100 * sub_ok / sub_total if sub_total else 0.0,
    )


def diff_counts(
    lang: str,
    prefix: str,
    config: str,
    splits: tuple[str, ...] = ("test", "dev"),
    greedy: bool = False,
) -> tuple[int, int]:
    """Improved/worsened token counts, baseline vs config. NB: the strategies
    read their config at CALL time, so the baseline pass runs entirely
    OUTSIDE the patched() context and the candidate pass entirely inside."""
    tokens = list(iter_eval_tokens(prefix, splits))
    base_lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=greedy))
    base_out = [base_lem.lemmatize(form, lang=lang) for form, _ in tokens]
    with patched(config):
        cand_lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=greedy))
        cand_out = [cand_lem.lemmatize(form, lang=lang) for form, _ in tokens]
    improved = worsened = 0
    for (form, lemma), b, a in zip(tokens, base_out, cand_out):
        if a == b:
            continue
        if b == lemma and a != lemma:
            worsened += 1
        elif a == lemma and b != lemma:
            improved += 1
    return improved, worsened


def passes_sign_test(improved: int, worsened: int) -> bool:
    "Net must clear noise, not just be positive."
    if improved + worsened == 0:
        return False
    return improved >= worsened + 2 * math.sqrt(improved + worsened)


def verdict(
    tune_improved: int,
    tune_worsened: int,
    confirm_improved: int,
    confirm_worsened: int,
) -> str:
    """'reject' / 'borderline' / 'accept' per the pre-registered protocol
    (see module docstring); 'borderline' needs the manual diff-token audit
    before treating as a signal. Status quo wins all ties."""
    if not passes_sign_test(tune_improved, tune_worsened):
        return "reject"
    confirm_net = confirm_improved - confirm_worsened
    if confirm_net <= 0:
        return "reject"
    if passes_sign_test(confirm_improved, confirm_worsened):
        return "accept"
    return "borderline"


def greedy_leg(lang: str, prefix: str, new_gate: int) -> bool:
    """Greedy-mode regression check for a gate change: the gate is shared
    with GreedyDictionaryLookupStrategy, so shipping it retunes greedy=True
    users too. Patches BOTH modules (unlike the `gate:` config, which
    correctly patches only the affix side for the non-greedy protocol).
    Returns True if shippable (no regression beyond noise)."""
    saved = (getattr(AD, "greedy_min_length"), GDL.greedy_min_length)
    base_fn = saved[0]

    def per_lang(lg: str, _base: Any = base_fn) -> int:
        return int(new_gate if lg == lang else _base(lg))

    tokens = list(iter_eval_tokens(prefix))
    base_lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True))
    base_out = [base_lem.lemmatize(form, lang=lang) for form, _ in tokens]
    try:
        setattr(AD, "greedy_min_length", per_lang)
        setattr(GDL, "greedy_min_length", per_lang)
        cand_lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=True))
        cand_out = [cand_lem.lemmatize(form, lang=lang) for form, _ in tokens]
    finally:
        setattr(AD, "greedy_min_length", saved[0])
        setattr(GDL, "greedy_min_length", saved[1])
    improved = worsened = 0
    for (form, lemma), b, a in zip(tokens, base_out, cand_out):
        if a == b:
            continue
        if b == lemma and a != lemma:
            worsened += 1
        elif a == lemma and b != lemma:
            improved += 1
    n = improved + worsened
    regression = n > 0 and worsened >= improved + 2 * math.sqrt(n)
    print(
        f"greedy leg {lang} gate->{new_gate}: improved={improved} worsened={worsened}"
    )
    return not regression


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    lang, prefix = sys.argv[1], sys.argv[2]
    print(
        f"{'config':16} {'tokens':>7} {'acc%':>8} {'oov_n':>6} {'oov_acc%':>8} "
        f"{'tune i/w':>9} {'confirm i/w':>11} {'verdict':>10}"
    )
    for config in ["baseline"] + sys.argv[3:]:
        total, acc, sub_n, sub_acc = run(lang, prefix, config)
        if config == "baseline":
            print(f"{config:16} {total:7d} {acc:8.3f} {sub_n:6d} {sub_acc:8.2f}")
            continue
        ti, tw = diff_counts(lang, prefix, config, splits=("dev",))
        ci, cw = diff_counts(lang, prefix, config, splits=("test",))
        print(
            f"{config:16} {total:7d} {acc:8.3f} {sub_n:6d} {sub_acc:8.2f} "
            f"{f'{ti}/{tw}':>9} {f'{ci}/{cw}':>11} {verdict(ti, tw, ci, cw):>10}"
        )


if __name__ == "__main__":
    main()
