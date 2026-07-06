"""
Diff-token audit: the manual-inspection gate every accepted UD delta must
pass (a harm class concentrated in one POS or lexical pattern is a red flag
even when net counts look fine).

Three modes, one classifier:

--config <cfg> <lang> <ud_prefix>
    Diff baseline vs. a runtime-patched candidate config (any string
    training/ud_end_to_end.patched() accepts).

--worktree <path> [lang ...]
    Diff the current working tree against another simplemma checkout.
    Each side runs in a SUBPROCESS (the `dump` subcommand) with an explicit
    package root, since Python can't hold two simplemma versions in one
    process. Create the comparison worktree first:
        git worktree add /tmp/simplemma_main_worktree <ref> --detach
    (remove it afterwards to avoid a dangling .git/worktrees/ entry). The
    dump worker keeps its own conllu reader: importing training.ud_eval
    there could resolve against the OTHER tree, which may predate it.

--consistency <lang> <ud_prefix>
    Flag words the CURRENT rules module changes despite the treebank
    showing them as consistently gold (n>=2, single lemma across every
    occurrence). Identity mismatches are stoplist candidates; non-identity
    mismatches are rule bugs. An inconsistent gold is annotation noise, not
    a stoplist candidate.
"""

import csv
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = str(REPO_ROOT / "training" / "data" / "rules_eval" / "results")

# lang -> UD prefix. ms has no treebank (in-dict-only risk).
LANG_TREEBANKS = {
    "ca": "ca_ancora",
    "cs": "cs_cac",
    "en": "en_ewt",
    "eo": "eo_prago",  # eo_cairo also exists, unused
    "es": "es_gsd",
    "et": "et_edt",
    "fi": "fi_tdt",
    "gl": "gl_ctg",  # tune split; gl_treegal is the confirm set
    "is": "is_modern",  # ~59% dict agreement, see ud_eval.reliability
    "ka": "ka_glc",  # gained train+dev in UD v2.18
    "la": "la_ittb",
    "lb": "lb_luxbank",  # test-only treebank
    "lv": "lv_lvtb",
    "mk": "mk_mtb",
    "nl": "nl_alpino",
    "nn": "no_nynorsk",
    "pl": "pl_pdb",
    "pt": "pt_bosque",  # tune split; pt_porttinari is the confirm set
    "ro": "ro_rrt",  # ro_simonero/ro_nonstandard are domain-mismatch traps
    "ru": "ru_gsd",
    "se": "sme_giella",  # no dev split upstream
    "sk": "sk_snk",
    "sl": "sl_ssj",
    "sv": "sv_talbanken",
    "uk": "uk_iu",
    "de": "de_gsd",  # dev-only, compound-gold laziness
}

Row = tuple[str, str, str]  # (form, lemma, upos)


def _report(
    header: str,
    tokens: list[Row],
    base_out: list[str],
    cand_out: list[str],
    n_examples: int = 15,
) -> None:
    improved = worsened = neutral = 0
    upos_worse: Counter[str] = Counter()
    seen: set[tuple[str, str, str]] = set()
    samples_worse: list[tuple[str, str, str, str, str]] = []
    samples_better: list[tuple[str, str, str, str, str]] = []
    id_gold_worse = 0
    for (form, lemma, upos), b, a in zip(tokens, base_out, cand_out):
        if a == b:
            continue
        if b == lemma and a != lemma:
            worsened += 1
            upos_worse[upos] += 1
            id_gold_worse += lemma == form
            kind = "worse"
        elif a == lemma and b != lemma:
            improved += 1
            kind = "better"
        else:
            neutral += 1
            kind = "neutral"
        key = (kind, form, lemma)
        if key not in seen:
            seen.add(key)
            if kind == "worse" and len(samples_worse) < n_examples:
                samples_worse.append((form, b, a, lemma, upos))
            elif kind == "better" and len(samples_better) < 6:
                samples_better.append((form, b, a, lemma, upos))
    print(f"=== {header} ===")
    print(
        f"  n={len(tokens)} improved={improved} worsened={worsened} neutral={neutral}"
    )
    if worsened:
        print(f"  worsened upos: {dict(upos_worse.most_common())}")
        print(
            f"  identity-gold share of worsened: {100 * id_gold_worse / worsened:.0f}%"
        )
    for form, b, a, lemma, upos in samples_worse:
        print(f"  WORSE [{upos}] {form}: {b} -> {a}  (gold {lemma})")
    for form, b, a, lemma, upos in samples_better:
        print(f"  better [{upos}] {form}: {b} -> {a}  (gold {lemma})")
    print(flush=True)


# ---------- config mode ----------


def audit_config(lang: str, prefix: str, config: str, greedy: bool = False) -> None:
    from simplemma import Lemmatizer
    from simplemma.strategies.default import DefaultStrategy
    from training.ud_end_to_end import patched
    from training.ud_eval import iter_tokens

    tokens = list(iter_tokens(prefix, splits=("test", "dev")))
    base_lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=greedy))
    base_out = [base_lem.lemmatize(form, lang=lang) for form, _, _ in tokens]
    with patched(config):
        cand_lem = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=greedy))
        cand_out = [cand_lem.lemmatize(form, lang=lang) for form, _, _ in tokens]
    _report(f"{lang} {config}", tokens, base_out, cand_out)


# ---------- worktree mode ----------


def _eval_tokens(ud_dir: str, prefix: str) -> list[Row]:
    "Worker-local reader (see module docstring for why it is not shared)."
    import glob

    files = [
        f
        for split in ("test", "dev")
        for f in glob.glob(os.path.join(ud_dir, f"{prefix}-ud-{split}.conllu"))
    ]
    assert files, f"no conllu files for {prefix} in {ud_dir}"
    out = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                cols = line.split("\t")
                if "-" in cols[0] or "." in cols[0] or cols[2] == "_":
                    continue
                form = cols[1].lower() if cols[0] == "1" else cols[1]
                out.append((form, cols[2], cols[3]))
    return out


def run_dump(pkg_root: str, lang: str, ud_dir: str, prefix: str, out_csv: str) -> None:
    "Worker: lemmatize every eval token using the simplemma at pkg_root."
    sys.path.insert(0, pkg_root)
    from simplemma import Lemmatizer
    from simplemma.strategies.default import DefaultStrategy

    module_path = getattr(sys.modules["simplemma"], "__file__", None)
    assert module_path is not None
    assert os.path.commonpath([module_path, pkg_root]) == os.path.normpath(pkg_root), (
        f"simplemma resolved outside {pkg_root}: {module_path}"
    )

    lemmatizer = Lemmatizer(lemmatization_strategy=DefaultStrategy(greedy=False))
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(("form", "gold", "upos", "predicted"))
        for form, gold, upos in _eval_tokens(ud_dir, prefix):
            writer.writerow((form, gold, upos, lemmatizer.lemmatize(form, lang=lang)))


def _dump(pkg_root: str, lang: str, prefix: str, out_csv: str) -> None:
    from training.ud_eval import UD_DIR

    subprocess.run(
        [
            sys.executable,
            os.path.abspath(__file__),
            "dump",
            pkg_root,
            lang,
            UD_DIR,
            prefix,
            out_csv,
        ],
        cwd=str(REPO_ROOT),
        check=True,
    )


def _read_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def audit_worktree(worktree: str, langs: list[str]) -> None:
    unknown = sorted(set(langs) - set(LANG_TREEBANKS))
    if unknown:
        sys.exit(
            f"no treebank mapping for: {', '.join(unknown)} "
            f"(known: {', '.join(sorted(LANG_TREEBANKS))})"
        )
    os.makedirs(OUT_DIR, exist_ok=True)
    for lang in langs or sorted(LANG_TREEBANKS):
        prefix = LANG_TREEBANKS[lang]
        old_csv = os.path.join(OUT_DIR, f"{lang}_old.csv")
        new_csv = os.path.join(OUT_DIR, f"{lang}_new.csv")
        _dump(worktree, lang, prefix, old_csv)
        _dump(str(REPO_ROOT), lang, prefix, new_csv)
        old_rows, new_rows = _read_csv(old_csv), _read_csv(new_csv)
        assert len(old_rows) == len(new_rows)
        tokens = [(r["form"], r["gold"], r["upos"]) for r in new_rows]
        _report(
            f"{lang} ({prefix}) worktree-vs-current",
            tokens,
            [r["predicted"] for r in old_rows],
            [r["predicted"] for r in new_rows],
        )


# ---------- consistency mode ----------


def audit_consistency(lang: str, prefix: str, n_examples: int = 20) -> None:
    from simplemma.strategies.defaultrules import RULE_FUNCTIONS
    from training.ud_eval import iter_tokens

    apply_fn = RULE_FUNCTIONS.get(lang)
    if apply_fn is None:
        sys.exit(f"no rules registered for {lang!r} in defaultrules/__init__.py")
    gold: dict[str, Counter[str]] = defaultdict(Counter)
    for form, lemma, _ in iter_tokens(prefix, splits=("train", "dev", "test")):
        gold[form][lemma] += 1

    stoplist_candidates: list[tuple[str, int, str]] = []
    mismatches: list[tuple[str, int, str, str]] = []
    for form, counter in gold.items():
        total = sum(counter.values())
        if total < 2 or len(counter) != 1:
            continue  # inconsistent gold is annotation noise, not signal
        (majority_lemma,) = counter
        out = apply_fn(form)
        if out is None or out == majority_lemma:
            continue
        if majority_lemma == form:
            stoplist_candidates.append((form, total, out))
        else:
            mismatches.append((form, total, out, majority_lemma))

    stoplist_candidates.sort(key=lambda r: -r[1])
    mismatches.sort(key=lambda r: -r[1])
    print(f"=== {lang} ({prefix}) consistency scan ===")
    print(f"  stoplist candidates (n={len(stoplist_candidates)}):")
    for form, total, out in stoplist_candidates[:n_examples]:
        print(f"    {form} (n={total}): rules -> {out}  (gold {form})")
    print(f"  non-identity mismatches (n={len(mismatches)}):")
    for form, total, out, majority_lemma in mismatches[:n_examples]:
        print(f"    {form} (n={total}): rules -> {out}  (gold {majority_lemma})")


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "dump":
        _, pkg_root, lang, ud_dir, prefix, out_csv = args
        run_dump(pkg_root, lang, ud_dir, prefix, out_csv)
    elif args and args[0] == "--config" and len(args) >= 4:
        greedy = "--greedy" in args
        positional = [a for a in args[1:] if a != "--greedy"]
        config, lang, prefix = positional[:3]
        audit_config(lang, prefix, config, greedy=greedy)
    elif args and args[0] == "--worktree" and len(args) >= 2:
        audit_worktree(args[1], args[2:])
    elif args and args[0] == "--consistency" and len(args) >= 3:
        audit_consistency(args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
