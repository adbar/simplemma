"""
UD treebank reading and data-quality diagnostics for the rules/affix
evaluation toolkit.

Conventions mirror training/evaluate_simplemma.py: skip lemma == "_",
lowercase sentence-initial forms, exact-match scoring. Reads the per-split
files under training/data/UD/splits/ (fetched by download_eval_data.py),
not the concatenated ones evaluate_simplemma.py consumes -- the tune/confirm
protocol needs the dev/test split boundary preserved.

CLI:
    uv run python -m training.ud_eval reliability <lang:prefix> [...]
    uv run python -m training.ud_eval pos-coverage <lang:prefix> [...]
"""

import glob
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from simplemma.strategies.dictionary_lookup import (  # noqa: E402
    DictionaryLookupStrategy,
)

UD_DIR = str(REPO_ROOT / "training" / "data" / "UD" / "splits")

Token = tuple[str, str, str]  # (form, lemma, upos)


def _iter_rows(
    lang_prefix: str,
    splits: tuple[str, ...] = ("train", "dev", "test"),
    ud_dir: str = UD_DIR,
) -> Iterator[list[str]]:
    """Token rows (CONLL-U columns) with the toolkit's reading conventions
    applied once: comments/MWT/empty nodes/lemma=='_' skipped,
    sentence-initial forms lowercased."""
    files = sorted(
        f
        for split in splits
        for f in glob.glob(os.path.join(ud_dir, f"{lang_prefix}-ud-{split}.conllu"))
    )
    assert files, f"no conllu files for {lang_prefix} splits={splits}"
    for path in files:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                cols = line.rstrip("\n").split("\t")
                if "-" in cols[0] or "." in cols[0] or cols[2] == "_":
                    continue
                if cols[0] == "1":
                    cols[1] = cols[1].lower()
                yield cols


def iter_tokens(
    lang_prefix: str,
    splits: tuple[str, ...] = ("train", "dev", "test"),
    ud_dir: str = UD_DIR,
) -> Iterator[Token]:
    "Yield (form, lemma, upos) over the given splits of one treebank."
    for cols in _iter_rows(lang_prefix, splits, ud_dir):
        yield cols[1], cols[2], cols[3]


def oov_types(
    lang: str,
    lang_prefix: str,
    dict_lookup: DictionaryLookupStrategy,
    capitalized: bool = False,
) -> list[tuple[str, str, int]]:
    """Alphabetic types NOT resolved by dictionary lookup, with majority gold
    lemma and token frequency. capitalized=True selects capitalized-initial
    types instead of lowercase-initial."""
    gold: dict[str, Counter[str]] = defaultdict(Counter)
    for form, lemma, _ in iter_tokens(lang_prefix):
        if form.isalpha() and form[:1].isupper() == capitalized:
            gold[form][lemma] += 1
    out = []
    for form, counter in gold.items():
        if dict_lookup.get_lemma(form, lang) is None:
            lemma, _ = counter.most_common(1)[0]
            out.append((form, lemma, sum(counter.values())))
    return out


def reliability(lang: str, prefix: str) -> dict[str, float]:
    """Annotation-quality profile; consult before trusting a UD verdict that
    falls in a known-noisy class (e.g. es-GSD PROPN lowercasing).
      inconsistency: share of (form, upos) types (n>=5) off the majority lemma
      plur_id: NOUN Number=Plur tokens whose gold lemma == form
      propn_id: PROPN tokens whose gold lemma == form
      dict_agree: dict-resolved lowercase alpha tokens where gold == dict"""
    lookup = DictionaryLookupStrategy()
    looked_up: dict[str, str | None] = {}
    lemmas_by_type: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    n = plur = plur_id = propn = propn_id = indict = agree = 0
    for cols in _iter_rows(prefix):
        form, lemma, upos, feats = cols[1], cols[2], cols[3], cols[5]
        n += 1
        lemmas_by_type[(form, upos)][lemma] += 1
        if upos == "NOUN" and "Number=Plur" in feats:
            plur += 1
            plur_id += lemma == form
        elif upos == "PROPN":
            propn += 1
            propn_id += lemma == form
        if form[:1].islower() and form.isalpha():
            if form not in looked_up:
                looked_up[form] = lookup.get_lemma(form, lang)
            d = looked_up[form]
            if d is not None:
                indict += 1
                agree += d == lemma
    big = {k: c for k, c in lemmas_by_type.items() if sum(c.values()) >= 5}
    tok = sum(sum(c.values()) for c in big.values())
    maj = sum(c.most_common(1)[0][1] for c in big.values())
    return {
        "tokens": float(n),
        "inconsistency_pct": 100 * (tok - maj) / tok if tok else 0.0,
        "plur_id_pct": 100 * plur_id / plur if plur else 0.0,
        "propn_id_pct": 100 * propn_id / propn if propn else 0.0,
        "dict_agree_pct": 100 * agree / indict if indict else 0.0,
    }


_POS_GROUPS = {
    "ADV": "ADV",
    "ADP": "FUNC",
    "CCONJ": "FUNC",
    "SCONJ": "FUNC",
    "PART": "FUNC",
    "PRON": "FUNC",
    "DET": "FUNC",
    "NOUN": "NOUN",
    "VERB": "VERB",
    "ADJ": "ADJ",
}
_POS_ORDER = ("ADV", "FUNC", "NOUN", "VERB", "ADJ")


def pos_coverage(lang: str, prefix: str) -> dict[str, tuple[float, float]]:
    """Per-POS-group dictionary OOV rates (token%, type%)."""
    lookup = DictionaryLookupStrategy()
    is_oov: dict[str, bool] = {}
    tok: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    typ: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    seen: set[tuple[str, str]] = set()
    for form, _, upos in iter_tokens(prefix):
        group = _POS_GROUPS.get(upos)
        if group is None or not form.isalpha():
            continue
        if form not in is_oov:
            is_oov[form] = lookup.get_lemma(form, lang) is None
        oov = is_oov[form]
        tok[group][0] += 1
        tok[group][1] += oov
        if (form, group) not in seen:
            seen.add((form, group))
            typ[group][0] += 1
            typ[group][1] += oov
    out = {}
    for group in _POS_ORDER:
        tn, to = tok[group]
        yn, yo = typ[group]
        out[group] = (
            100 * to / tn if tn else 0.0,
            100 * yo / yn if yn else 0.0,
        )
    return out


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("reliability", "pos-coverage"):
        print(__doc__)
        sys.exit(1)
    mode = sys.argv[1]
    pairs = [arg.split(":", 1) for arg in sys.argv[2:]]
    if mode == "reliability":
        print(
            f"{'lang':4} {'tokens':>8} {'inconsist%':>10} {'plurN_id%':>9} "
            f"{'propn_id%':>9} {'dict_agree%':>11}"
        )
        for lang, prefix in pairs:
            r = reliability(lang, prefix)
            print(
                f"{lang:4} {int(r['tokens']):8d} {r['inconsistency_pct']:10.2f} "
                f"{r['plur_id_pct']:9.1f} {r['propn_id_pct']:9.1f} "
                f"{r['dict_agree_pct']:11.1f}"
            )
    else:
        header = f"{'lang':4} " + " ".join(f"{g:>15}" for g in _POS_ORDER)
        print(header + "   (token-OOV% / type-OOV%)")
        for lang, prefix in pairs:
            cov = pos_coverage(lang, prefix)
            cells = [f"{cov[g][0]:5.1f}/{cov[g][1]:5.1f}    " for g in _POS_ORDER]
            print(f"{lang:4} " + " ".join(cells))


if __name__ == "__main__":
    main()
