import csv

import pytest
from conllu import parse

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.strategies.dictionaries import DefaultDictionaryFactory
from training import evaluate_simplemma
from training.evaluate_simplemma import evaluate_dataset

from .conftest import FixedMapping

# base-form tokens (form == lemma): tests the counting logic, not accuracy
CONLLU = (
    "1\trun\trun\tVERB\t_\t_\t0\troot\t_\t_\n"
    "2\tfast\tfast\tADJ\t_\t_\t1\tadvmod\t_\t_\n"
    "3\tcat\tcat\tNOUN\t_\t_\t1\tnsubj\t_\t_\n"
    "\n"
)

# OOV token (guaranteed error) + a lemma == "_" token (skipped)
CONLLU_ERRORS = (
    "1\tqwxztest\tqwxzlemma\tVERB\t_\t_\t0\troot\t_\t_\n"
    "2\tword\t_\tNOUN\t_\t_\t1\tdep\t_\t_\n"
    "\n"
)


@pytest.fixture
def lemmatizers() -> tuple[Lemmatizer, Lemmatizer]:
    factory = DefaultDictionaryFactory()
    return (
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(
                greedy=False, dictionary_factory=factory
            )
        ),
        Lemmatizer(
            lemmatization_strategy=DefaultStrategy(
                greedy=True, dictionary_factory=factory
            )
        ),
    )


def test_evaluate_dataset(lemmatizers):
    lemmatizer, greedy_lemmatizer = lemmatizers
    overall, focus, _ = evaluate_dataset(
        parse(CONLLU), lemmatizer, greedy_lemmatizer, "en"
    )

    assert overall.total == 3
    assert overall.baseline == 3
    assert focus.total == 2
    assert focus.baseline == 2


def test_evaluate_dataset_errors_and_skip(lemmatizers):
    lemmatizer, greedy_lemmatizer = lemmatizers
    overall, _, errors = evaluate_dataset(
        parse(CONLLU_ERRORS), lemmatizer, greedy_lemmatizer, "en"
    )

    assert overall.total == 1
    assert overall.baseline == 0
    assert len(errors) == 1
    assert errors[0][0] == "qwxztest"


def test_evaluate_dataset_canonicalizes_ar_gold_lemma():
    """PADT gold lemmas are vocalized; the dict is built from unvocalized
    forms, so the gold lemma must be canonicalized before comparison or
    every ar content lemma mismatches."""

    mapping = {"كتاب": "كتاب"}  # unvocalized key/value
    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=FixedMapping(mapping))
    )
    conllu = "1\tكتاب\tكِتَاب\tNOUN\t_\t_\t0\troot\t_\t_\n\n"  # vocalized gold
    overall, _, errors = evaluate_dataset(parse(conllu), lemmatizer, lemmatizer, "ar")
    assert overall.total == 1
    assert overall.nongreedy == 1  # matches only because gold was canonicalized
    assert not errors


def test_main_writes_results(tmp_path):
    """A dataset is scored over its held-out splits chained (dev+test); train
    is excluded -- it feeds the override mining AND calibrates the gate."""
    splits = tmp_path / "splits"
    splits.mkdir()
    (splits / "en_test-ud-train.conllu").write_text(CONLLU, encoding="utf-8")
    (splits / "en_test-ud-dev.conllu").write_text(CONLLU, encoding="utf-8")
    (splits / "en_test-ud-test.conllu").write_text(CONLLU, encoding="utf-8")
    results = tmp_path / "results"

    # run twice: the second call exercises the results-folder reset branch
    evaluate_simplemma.main(splits, results)
    evaluate_simplemma.main(splits, results)

    with open(results / "results_summary.csv", newline="", encoding="utf-8") as fh:
        rows = {row[0]: row for row in csv.reader(fh)}
    assert "dataset" in rows  # header
    assert rows["en_test"][2] == "6"  # dev+test counted, train's 3 tokens not
    assert (results / "en_test.csv").exists()


def test_main_skips_train_only_dataset(tmp_path):
    """A dataset with ONLY a train split yields nothing to score."""
    splits = tmp_path / "splits"
    splits.mkdir()
    (splits / "en_test-ud-train.conllu").write_text(CONLLU, encoding="utf-8")
    results = tmp_path / "results"

    evaluate_simplemma.main(splits, results)
    assert "en_test" not in (results / "results_summary.csv").read_text()


def test_main_requires_data(tmp_path):
    with pytest.raises(Exception, match="doesn't seem like data"):
        evaluate_simplemma.main(tmp_path / "missing", tmp_path / "results")


def test_main_maps_dataset_name_to_lang(tmp_path):
    """A UD prefix that isn't the ISO code (no_nynorsk) must go through dataset_to_lang."""
    splits = tmp_path / "splits"
    splits.mkdir()
    (splits / "no_nynorsk-ud-test.conllu").write_text(CONLLU, encoding="utf-8")
    results = tmp_path / "results"

    evaluate_simplemma.main(splits, results)  # would raise ValueError('no') pre-fix
    assert "no_nynorsk" in (results / "results_summary.csv").read_text()
