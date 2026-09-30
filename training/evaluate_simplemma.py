"""Published evaluation on the held-out UD dev and test splits.

Train is excluded because override mining and eval_gate use it.
"""

import csv
import logging
import shutil
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.utils import canonicalize_token
from training.ud_conllu import (
    UD_SPLITS,
    dataset_name,
    dataset_to_lang,
    iter_word_tokens,
)

log = logging.getLogger(__name__)

RESULTS_FOLDER = Path(__file__).parent / "data" / "results"


@dataclass
class Tally:
    """Match counts for one token bucket (all tokens, or ADJ+NOUN focus)."""

    total: int = 0
    greedy: int = 0
    nongreedy: int = 0
    baseline: int = 0  # form == lemma

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
    tokens: Iterable[tuple[str, Any]],
    lemmatizer: Lemmatizer,
    greedy_lemmatizer: Lemmatizer,
    language: str,
) -> tuple[Tally, Tally, list[tuple[str, str, str, str]]]:
    """(overall tally, ADJ+NOUN tally, error rows) over `iter_word_tokens` pairs."""
    overall = Tally()
    focus = Tally()
    errors: list[tuple[str, str, str, str]] = []

    for token_form, token in tokens:
        lemma = token["lemma"]
        candidate = lemmatizer.lemmatize(token_form, lang=language)
        greedy_candidate = greedy_lemmatizer.lemmatize(token_form, lang=language)
        greedy_ok = greedy_candidate == lemma
        nongreedy_ok = candidate == lemma
        # Canonicalized to match the gold's key space.
        baseline_ok = canonicalize_token(token["form"], language) == lemma

        overall.add(greedy_ok, nongreedy_ok, baseline_ok)
        if token["upos"] in ("ADJ", "NOUN"):
            focus.add(greedy_ok, nongreedy_ok, baseline_ok)
        if not (greedy_ok and nongreedy_ok):
            errors.append((token["form"], lemma, candidate, greedy_candidate))

    return overall, focus, errors


def main(
    splits_folder: Path = UD_SPLITS,
    results_folder: Path = RESULTS_FOLDER,
) -> None:
    if not splits_folder.exists():
        raise Exception(
            "It doesn't seem like data was downloaded and processed for evaluation."
        )

    datasets: defaultdict[str, list[Path]] = defaultdict(list)
    for path in sorted(splits_folder.glob("*-ud-*.conllu")):
        if path.name.endswith("-ud-train.conllu"):
            continue
        datasets[dataset_name(path)].append(path)

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

        lemmatizer = Lemmatizer(lemmatization_strategy=DefaultStrategy())
        greedy_lemmatizer = Lemmatizer(
            lemmatization_strategy=DefaultStrategy(greedy=True)
        )

        for dataset, paths in datasets.items():
            start = time.time()
            log.info(f"Evaluating dataset: {dataset}")
            language = dataset_to_lang(dataset)
            overall, focus, errors = evaluate_dataset(
                chain.from_iterable(iter_word_tokens(p, language) for p in paths),
                lemmatizer,
                greedy_lemmatizer,
                language,
            )

            if overall.total > 0:
                csv_results_file_writer.writerow(
                    (
                        dataset,
                        time.time() - start,
                        overall.total,
                        *overall.ratios(),
                        *focus.ratios(),
                    )
                )

            with open(
                results_folder / f"{dataset}.csv",
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
