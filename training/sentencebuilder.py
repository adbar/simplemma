"""Regenerate the sentence-starter lists that `simplemma.sentences` ships.

At every '.'-junction the splitter suppresses, gold either puts a boundary
or not, so a candidate's verdict is two counters. Mine on the *-ud-train
splits, adopt only if it beats the shipped list on *-ud-dev (train would be
circular; dev costs nothing published -- the reported metric is PUD F1). No
dev treebank (se, gv) falls back to test, with a warning.

Abbreviations are deliberately not mined: worth +0.0002-0.0025 F1 held out,
vs up to +0.09 for starters.

Usage: uv run python -m training.sentencebuilder <lang> [--check]
"""

import argparse
import textwrap
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import simplemma.sentences as sentences
from simplemma.utils import normalize_token
from training.eval_gate import discover_treebanks
from training.ud_conllu import UD_SPLITS

MIN_SUPPORT = 2  # junctions a candidate must fix before it earns an entry


def gold_sentences(path: Path) -> list[str]:
    """The '# text =' lines, i.e. the gold segmentation without token parsing.
    Streamed: a treebank is up to 200 MB, and only these lines are needed."""
    with path.open(encoding="utf-8", errors="replace") as filehandle:
        return [
            text
            for line in filehandle
            if line.startswith("# text = ") and (text := line[9:].strip())
        ]


def sentence_ends(gold: list[str], joiner: str) -> set[int]:
    """Offsets one past each sentence in `joiner.join(gold)`, last one excluded."""
    ends = set()
    cursor = 0
    for sentence in gold[:-1]:
        cursor += len(sentence)
        ends.add(cursor)
        cursor += len(joiner)
    return ends


def mine(lang: str, golds: list[list[str]]) -> tuple[Counter[str], Counter[str]]:
    """Per candidate starter: suppressed junctions where gold does put a
    boundary (gain) and where it does not (loss)."""
    terminators, junction, abbrevs, _ = sentences._profile(lang)
    gain: Counter[str] = Counter()
    loss: Counter[str] = Counter()
    for gold in golds:
        if len(gold) < 2:
            continue
        text = " ".join(gold)
        starts = {end + 1 for end in sentence_ends(gold, " ")}
        for match in junction.finditer(text):
            pos, after = match.span()
            if text[pos] != ".":
                continue
            # start=0, so the window check differs from the splitter's for a
            # junction within _WINDOW of a boundary: this only proposes, the
            # held-out gate below is what decides
            if sentences._dot_verdict(text, 0, pos, terminators, abbrevs) is not True:
                continue  # some other rule owns this junction
            word = sentences._WORD.match(text, after, after + 30)
            if word is None:
                continue
            token = word.group()
            if token[:1].isalpha():  # not '(', '***', '12'
                counts = gain if after in starts else loss
                counts[normalize_token(token.lower())] += 1
    return gain, loss


def select(gain: Counter[str], loss: Counter[str]) -> frozenset[str]:
    """The whole acceptance rule: fix more junctions than you break, with
    support. A threshold ladder measured no better than this."""
    return frozenset(
        word for word, hits in gain.items() if hits >= MIN_SUPPORT and hits > loss[word]
    )


def boundary_f1(lang: str, golds: list[list[str]]) -> float:
    """Mean sentence-boundary F1 over `golds`, in both registers."""
    scores = []
    for gold in golds:
        if len(gold) < 2:
            continue
        for joiner in (" ", "\n"):
            text = joiner.join(gold)
            expected = sentence_ends(gold, joiner)
            found: set[int] = set()
            cursor = 0
            for piece in sentences.split_sentences(text, lang)[:-1]:
                start = text.find(piece, cursor)
                if start >= 0:
                    cursor = start + len(piece)
                    found.add(cursor)
            # F1 over boundary offsets, as its Dice form
            scores.append(2 * len(expected & found) / (len(found) + len(expected)))
    return sum(scores) / len(scores) if scores else float("nan")


@contextmanager
def starters_replaced(lang: str, starters: frozenset[str]) -> Iterator[None]:
    """Swap in `starters` for `lang`, restoring on exit. `split_sentences`
    reads `_STARTERS` on every call, so mutating it is what the runtime sees."""
    previous = sentences._STARTERS.get(lang)
    sentences._STARTERS[lang] = starters
    try:
        yield
    finally:
        if previous is None:
            del sentences._STARTERS[lang]
        else:
            sentences._STARTERS[lang] = previous


def as_literal(lang: str, starters: frozenset[str]) -> str:
    """The mined list as a paste-able `_STARTERS` entry (ruff-format it after)."""
    # a hyphen is part of the entry, never a place to wrap
    chunks = textwrap.wrap(
        " ".join(sorted(starters)),
        width=68,
        break_on_hyphens=False,
        break_long_words=False,
    )
    body = "\n".join(f'        "{chunk} "' for chunk in chunks)
    return f'    "{lang}": frozenset(\n{body}\n        .split()\n    ),'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang", help="simplemma language code, e.g. 'de'")
    parser.add_argument(
        "--check", action="store_true", help="only score the shipped list"
    )
    args = parser.parse_args()

    held_out_split = "dev"
    paths = discover_treebanks(args.lang, "dev", ud_splits=UD_SPLITS)
    if not paths:
        # se/gv ship train+test treebanks but no dev
        held_out_split = "test"
        paths = discover_treebanks(args.lang, "test", ud_splits=UD_SPLITS)
        if paths:
            print(
                f"WARNING: no dev treebank for {args.lang!r}: scoring on TEST, "
                "a reported split"
            )
    if not paths:
        parser.error(f"no *-ud-dev or -test treebank for {args.lang!r} in {UD_SPLITS}")
    held_out = [gold_sentences(path) for path in paths]  # parsed once, scored twice
    shipped = boundary_f1(args.lang, held_out)
    print(
        f"shipped: {shipped:.5f} boundary F1 "
        f"over {len(paths)} {held_out_split} treebanks"
    )
    if args.check:
        return

    train = discover_treebanks(args.lang, "train", UD_SPLITS)
    mined = select(*mine(args.lang, [gold_sentences(path) for path in train]))
    with starters_replaced(args.lang, mined):
        candidate = boundary_f1(args.lang, held_out)
    print(f"mined {len(mined)}: {candidate:.5f} ({candidate - shipped:+.5f})")
    print(
        as_literal(args.lang, mined) if candidate > shipped else "keep the shipped list"
    )


if __name__ == "__main__":
    main()
