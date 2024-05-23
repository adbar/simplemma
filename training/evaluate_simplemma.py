import csv
import logging
import time

# from collections import Counter
from os import mkdir, path, rmdir, scandir, unlink

from conllu import parse_incr  # type: ignore

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.strategies.dictionaries import DefaultDictionaryFactory

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATA_FOLDER = path.join(path.dirname(__file__), "data")
CLEAN_DATA_FOLDER = path.join(DATA_FOLDER, "UD")
RESULTS_FOLDER = path.join(DATA_FOLDER, "results")

data_files = [
    (data_file.name.split("_")[0], data_file.name)
    for data_file in scandir(CLEAN_DATA_FOLDER)
]

if not path.exists(CLEAN_DATA_FOLDER):
    raise Exception(
        "It doesn't seem like data was downloaded and precessed for evaluation."
    )

if path.exists(RESULTS_FOLDER):
    for result_file in scandir(RESULTS_FOLDER):
        unlink(result_file)
    rmdir(RESULTS_FOLDER)
mkdir(RESULTS_FOLDER)

with open(path.join(RESULTS_FOLDER, "results_summary.csv"), "w") as csv_results_file:
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
        total = 0
        focus_total = 0
        greedy = 0
        nongreedy = 0
        zero = 0
        focus = 0
        focus_nongreedy = 0
        focus_zero = 0
        errors = []

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
        with open(
            path.join(CLEAN_DATA_FOLDER, filename), "r", encoding="utf-8"
        ) as data_file:
            for tokens in parse_incr(data_file):
                for token in tokens:
                    error_flag = False
                    if token["lemma"] == "_":  # or token['upos'] in ('PUNCT', 'SYM')
                        continue

                    initial = bool(token["id"] == 1)
                    token_form = token["form"].lower() if initial else token["form"]

                    candidate = lemmatizer.lemmatize(token_form, lang=language)
                    greedy_candidate = greedy_lemmatizer.lemmatize(
                        token_form, lang=language
                    )

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
                        greedy += 1
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

        if total > 0:
            csv_results_file_writer.writerow(
                (
                    filename.replace(".conllu", ""),
                    time.time() - start,
                    total,
                    (greedy / total) if total > 0 else 0,
                    (nongreedy / total) if total > 0 else 0,
                    (zero / total) if total > 0 else 0,
                    (focus / focus_total) if focus_total > 0 else 0,
                    (focus_nongreedy / focus_total) if focus_total > 0 else 0,
                    (focus_zero / focus_total) if focus_total > 0 else 0,
                )
            )

        with open(
            path.join(RESULTS_FOLDER, filename.replace("conllu", "csv")),
            "w",
            encoding="utf-8",
        ) as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(("form", "lemma", "candidate", "greedy_candidate"))
            writer.writerows(errors)

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
