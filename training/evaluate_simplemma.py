"""README-facing evaluation: score the full user-facing `Lemmatizer` over the
held-out UD *dev+test* splits, emitting published accuracy numbers,
greedy/baseline/ADJ+NOUN breakdowns, and per-dataset error CSVs.

Split discipline: train both feeds the override mining AND calibrates the
eval_gate, so it is the only split a shipping decision is ever made against.
That leaves dev and test genuinely held out, and both are reported here.

Distinct from `eval_harness`, which scores a bare strategy as a
dictionary-quality gate -- different protocol, not a duplicate.
"""

import csv
import logging
import shutil
import time
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from conllu import parse_incr

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.utils import canonicalize_token
from training.ud_conllu import UD_SPLITS, dataset_to_lang, iter_word_tokens_in_sentences

log = logging.getLogger(__name__)

RESULTS_FOLDER = Path(__file__).parent / "data" / "results"


@dataclass
class Tally:
    """Match counts for one token bucket (all tokens, or ADJ+NOUN focus)."""

    total: int = 0
    greedy: int = 0
    nongreedy: int = 0
    baseline: int = 0  # form == lemma ("do nothing")

    def add(self, greedy_ok: bool, nongreedy_ok: bool, baseline_ok: bool) -> None:
        self.total += 1
        self.greedy += greedy_ok
        self.nongreedy += nongreedy_ok
        self.baseline += baseline_ok

    def ratios(self) -> tuple[float, float, float]:
        """(greedy, nongreedy, baseline) accuracy; 0.0 for an empty bucket."""
        n = self.total or 1
        return self.greedy / n, self.nongreedy / n, self.baseline / n


def evaluate_dataset(
    sentences: Iterable[Any],
    lemmatizer: Lemmatizer,
    greedy_lemmatizer: Lemmatizer,
    language: str,
) -> tuple[Tally, Tally, list[tuple[str, str, str, str]]]:
    """Return (overall tally, ADJ+NOUN focus tally, error rows)."""
    overall = Tally()
    focus = Tally()
    errors: list[tuple[str, str, str, str]] = []

    for token_form, token in iter_word_tokens_in_sentences(sentences, language):
        # gold lemma already canonicalized in place by the iterator (no-op
        # outside _CANON_TABLES): e.g. PADT's vocalized gold compared in the
        # dict's unvocalized key space.
        lemma = token["lemma"]
        candidate = lemmatizer.lemmatize(token_form, lang=language)
        greedy_candidate = greedy_lemmatizer.lemmatize(token_form, lang=language)
        greedy_ok = greedy_candidate == lemma
        nongreedy_ok = candidate == lemma
        # form is only MWT-stripped by the iterator, not canonicalized like
        # the gold lemma -- canonicalize here so the identity baseline is
        # compared in the same key space (grc/he/ar).
        baseline_ok = canonicalize_token(token["form"], language) == lemma

        overall.add(greedy_ok, nongreedy_ok, baseline_ok)
        if token["upos"] in ("ADJ", "NOUN"):
            focus.add(greedy_ok, nongreedy_ok, baseline_ok)
        if not (greedy_ok and nongreedy_ok):
            errors.append((token["form"], lemma, candidate, greedy_candidate))

    return overall, focus, errors


def _iter_sentences(paths: list[Path]) -> Iterator[Any]:
    """Chain the parsed sentences of several conllu files, streaming."""
    for path in paths:
        with open(path, encoding="utf-8") as filehandle:
            yield from parse_incr(filehandle)


def main(
    splits_folder: Path = UD_SPLITS,
    results_folder: Path = RESULTS_FOLDER,
) -> None:
    if not splits_folder.exists():
        raise Exception(
            "It doesn't seem like data was downloaded and processed for evaluation."
        )

    # dev+test chained per dataset in sorted filename order; train excluded
    # (see the module docstring). dataset_to_lang: UD prefixes aren't always
    # the ISO code (no_nynorsk -> nn).
    datasets: defaultdict[str, list[Path]] = defaultdict(list)
    for path in sorted(splits_folder.glob("*-ud-*.conllu")):
        if path.name.endswith("-ud-train.conllu"):
            continue
        datasets[path.name.split("-ud-", 1)[0]].append(path)

    if results_folder.exists():
        shutil.rmtree(results_folder)
    results_folder.mkdir()

    with open(
        results_folder / "results_summary.csv", "w", newline="", encoding="utf-8"
    ) as csv_results_file:
        csv_results_file_writer = csv.writer(csv_results_file)
        csv_results_file_writer.writerow(
            (
                "dataset",
                "exec time",
                "token count",
                "greedy",
                "non-greedy",
                "baseline",
                "ADJ+NOUN greedy",
                "ADJ+NOUN non-greedy",
                "ADJ+NOUN baseline",
            )
        )

        # built once: token caches are lang-keyed, so reuse across datasets is safe
        lemmatizer = Lemmatizer(lemmatization_strategy=DefaultStrategy())
        greedy_lemmatizer = Lemmatizer(
            lemmatization_strategy=DefaultStrategy(greedy=True)
        )

        for dataset_name, paths in datasets.items():
            start = time.time()
            log.info(f"Evaluating dataset: {dataset_name}")
            overall, focus, errors = evaluate_dataset(
                _iter_sentences(paths),
                lemmatizer,
                greedy_lemmatizer,
                dataset_to_lang(dataset_name),
            )

            if overall.total > 0:
                csv_results_file_writer.writerow(
                    (
                        dataset_name,
                        time.time() - start,
                        overall.total,
                        *overall.ratios(),  # greedy, non-greedy, baseline
                        *focus.ratios(),  # ADJ+NOUN greedy, non-greedy, baseline
                    )
                )

            with open(
                results_folder / f"{dataset_name}.csv",
                "w",
                newline="",
                encoding="utf-8",
            ) as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(("form", "lemma", "candidate", "greedy_candidate"))
                writer.writerows(errors)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
