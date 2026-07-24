"""README-facing evaluation: score the full user-facing `Lemmatizer` over the
UD test treebanks, emitting published accuracy numbers, greedy/baseline/
ADJ+NOUN breakdowns, and per-dataset error CSVs.

Distinct from `eval_harness`, which scores a bare strategy as a
dictionary-quality gate -- different protocol, not a duplicate.
"""

import csv
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from conllu import parse_incr

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.utils import canonicalize_token
from training.ud_conllu import dataset_to_lang, iter_word_tokens_in_sentences

log = logging.getLogger(__name__)

DATA_FOLDER = Path(__file__).parent / "data"
CLEAN_DATA_FOLDER = DATA_FOLDER / "UD"
RESULTS_FOLDER = DATA_FOLDER / "results"


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


def main(
    clean_data_folder: Path = CLEAN_DATA_FOLDER,
    results_folder: Path = RESULTS_FOLDER,
) -> None:
    if not clean_data_folder.exists():
        raise Exception(
            "It doesn't seem like data was downloaded and precessed for evaluation."
        )

    # glob, not iterdir: the folder also holds UD_VERSION and splits/.
    # dataset_to_lang, not split('_')[0]: UD prefixes aren't always the ISO
    # code (no_nynorsk -> nn, sme_giella -> se).
    data_files = [
        (dataset_to_lang(data_file.stem), data_file.name)
        for data_file in clean_data_folder.glob("*.conllu")
    ]

    if results_folder.exists():
        for result_file in results_folder.iterdir():
            result_file.unlink()
        results_folder.rmdir()
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

        for language, filename in data_files:
            start = time.time()
            log.info(f"Evaluating dataset: {filename}")
            with open(clean_data_folder / filename, encoding="utf-8") as data_file:
                overall, focus, errors = evaluate_dataset(
                    parse_incr(data_file), lemmatizer, greedy_lemmatizer, language
                )

            if overall.total > 0:
                csv_results_file_writer.writerow(
                    (
                        filename.replace(".conllu", ""),
                        time.time() - start,
                        overall.total,
                        *overall.ratios(),  # greedy, non-greedy, baseline
                        *focus.ratios(),  # ADJ+NOUN greedy, non-greedy, baseline
                    )
                )

            with open(
                results_folder / filename.replace("conllu", "csv"),
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
