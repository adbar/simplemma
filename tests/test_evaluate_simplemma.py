from collections.abc import Mapping

import pytest
from conllu import parse

from simplemma import Lemmatizer
from simplemma.strategies import DictionaryFactory
from simplemma.strategies.default import DefaultStrategy
from simplemma.strategies.dictionaries import DefaultDictionaryFactory
from training import evaluate_simplemma
from training.evaluate_simplemma import evaluate_dataset

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

    class F(DictionaryFactory):
        def get_dictionary(self, lang: str) -> Mapping[str, str]:
            return {"كتاب": "كتاب"}  # unvocalized key/value

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=F())
    )
    conllu = "1\tكتاب\tكِتَاب\tNOUN\t_\t_\t0\troot\t_\t_\n\n"  # vocalized gold
    overall, _, errors = evaluate_dataset(parse(conllu), lemmatizer, lemmatizer, "ar")
    assert overall.total == 1
    assert overall.nongreedy == 1  # matches only because gold was canonicalized
    assert not errors


def test_main_writes_results(tmp_path):
    clean = tmp_path / "UD"
    clean.mkdir()
    (clean / "en_test.conllu").write_text(CONLLU, encoding="utf-8")
    # downloader-colocated decoys: main() must skip them (glob '*.conllu'), not crash
    (clean / "UD_VERSION").write_text("2.18", encoding="utf-8")
    (clean / "splits").mkdir()
    results = tmp_path / "results"

    # run twice: the second call exercises the results-folder reset branch
    evaluate_simplemma.main(clean, results)
    evaluate_simplemma.main(clean, results)

    summary = (results / "results_summary.csv").read_text()
    assert "dataset" in summary
    assert "en_test" in summary
    assert (results / "en_test.csv").exists()


def test_main_requires_data(tmp_path):
    with pytest.raises(Exception, match="doesn't seem like data"):
        evaluate_simplemma.main(tmp_path / "missing", tmp_path / "results")


def test_main_maps_dataset_name_to_lang(tmp_path):
    """A UD prefix that isn't the ISO code (no_nynorsk) must go through dataset_to_lang."""
    clean = tmp_path / "UD"
    clean.mkdir()
    (clean / "no_nynorsk.conllu").write_text(CONLLU, encoding="utf-8")
    results = tmp_path / "results"

    evaluate_simplemma.main(clean, results)  # would raise ValueError('no') pre-fix
    assert "no_nynorsk" in (results / "results_summary.csv").read_text()
