import csv
import logging
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from conllu import parse_incr

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.strategies.dictionaries import DefaultDictionaryFactory

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATA_FOLDER = Path(__file__).parent / "data"
CLEAN_DATA_FOLDER = DATA_FOLDER / "UD"
RESULTS_FOLDER = DATA_FOLDER / "results"


def evaluate_dataset(
    sentences: Iterable[Any],
    lemmatizer: Lemmatizer,
    greedy_lemmatizer: Lemmatizer,
    language: str,
) -> dict[str, Any]:
    total = 0
    focus_total = 0
    greedy_count = 0
    nongreedy = 0
    zero = 0
    focus = 0
    focus_nongreedy = 0
    focus_zero = 0
    errors: list[tuple[str, str, str, str]] = []

    for tokens in sentences:
        for token in tokens:
            error_flag = False
            if token["lemma"] == "_":  # or token['upos'] in ('PUNCT', 'SYM')
                continue

            initial = bool(token["id"] == 1)
            token_form = token["form"].lower() if initial else token["form"]

            candidate = lemmatizer.lemmatize(token_form, lang=language)
            greedy_candidate = greedy_lemmatizer.lemmatize(token_form, lang=language)

            if token["upos"] in ("ADJ", "NOUN"):
                focus_total += 1
                if token["form"] == token["lemma"]:
                    focus_zero += 1
                if greedy_candidate == token["lemma"]:
                    focus += 1
                if candidate == token["lemma"]:
                    focus_nongreedy += 1
            total += 1
            if token["form"] == token["lemma"]:
                zero += 1
            if greedy_candidate == token["lemma"]:
                greedy_count += 1
            else:
                error_flag = True
            if candidate == token["lemma"]:
                nongreedy += 1
            else:
                error_flag = True
            if error_flag:
                errors.append(
                    (token["form"], token["lemma"], candidate, greedy_candidate)
                )

    return {
        "total": total,
        "focus_total": focus_total,
        "greedy": greedy_count,
        "nongreedy": nongreedy,
        "zero": zero,
        "focus": focus,
        "focus_nongreedy": focus_nongreedy,
        "focus_zero": focus_zero,
        "errors": errors,
    }


def main(
    clean_data_folder: Path = CLEAN_DATA_FOLDER,
    results_folder: Path = RESULTS_FOLDER,
) -> None:
    if not clean_data_folder.exists():
        raise Exception(
            "It doesn't seem like data was downloaded and precessed for evaluation."
        )

    data_files = [
        (data_file.name.split("_")[0], data_file.name)
        for data_file in clean_data_folder.iterdir()
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

        for language, filename in data_files:
            start = time.time()
            _dictionary_factory = DefaultDictionaryFactory()
            lemmatizer = Lemmatizer(
                lemmatization_strategy=DefaultStrategy(
                    greedy=False, dictionary_factory=_dictionary_factory
                ),
            )
            greedy_lemmatizer = Lemmatizer(
                lemmatization_strategy=DefaultStrategy(
                    greedy=True, dictionary_factory=_dictionary_factory
                ),
            )
            log.info(f"Evaluating dataset: {filename}")
            with open(clean_data_folder / filename, encoding="utf-8") as data_file:
                result = evaluate_dataset(
                    parse_incr(data_file), lemmatizer, greedy_lemmatizer, language
                )

            total = result["total"]
            focus_total = result["focus_total"]

            if total > 0:
                csv_results_file_writer.writerow(
                    (
                        filename.replace(".conllu", ""),
                        time.time() - start,
                        total,
                        result["greedy"] / total,
                        result["nongreedy"] / total,
                        result["zero"] / total,
                        (result["focus"] / focus_total) if focus_total > 0 else 0,
                        (result["focus_nongreedy"] / focus_total)
                        if focus_total > 0
                        else 0,
                        (result["focus_zero"] / focus_total) if focus_total > 0 else 0,
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
                writer.writerows(result["errors"])

        # print("exec time:\t %.3f" % (time.time() - start))
        # print("token count:\t", total)
        # print("greedy:\t\t %.3f" % (greedy / total))
        # print("non-greedy:\t %.3f" % (nongreedy / total))
        # print("baseline:\t %.3f" % (zero / total))
        # print("ADJ+NOUN greedy:\t\t %.3f" % (focus / focus_total))
        # print("ADJ+NOUN non-greedy:\t\t %.3f" % (focus_nongreedy / focus_total))
        # print("ADJ+NOUN baseline:\t\t %.3f" % (focus_zero / focus_total))
        # mycounter = Counter(errors)
        # print(mycounter.most_common(20))


if __name__ == "__main__":
    main()
