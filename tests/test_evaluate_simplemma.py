import pytest
from conllu import parse

from simplemma import Lemmatizer
from simplemma.strategies.default import DefaultStrategy
from simplemma.strategies.dictionaries import DefaultDictionaryFactory
from training import evaluate_simplemma
from training.evaluate_simplemma import evaluate_dataset

# Single sentence: three base-form English tokens (form == lemma).
# Avoids dependence on lemmatizer accuracy — tests the counting logic only.
CONLLU = (
    "1\trun\trun\tVERB\t_\t_\t0\troot\t_\t_\n"
    "2\tfast\tfast\tADJ\t_\t_\t1\tadvmod\t_\t_\n"
    "3\tcat\tcat\tNOUN\t_\t_\t1\tnsubj\t_\t_\n"
    "\n"
)

# OOV token with wrong gold lemma (guaranteed error) + token with lemma "_" (skipped).
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
    result = evaluate_dataset(parse(CONLLU), lemmatizer, greedy_lemmatizer, "en")

    assert result["total"] == 3
    assert result["zero"] == 3  # all form == lemma
    assert result["focus_total"] == 2  # ADJ + NOUN
    assert result["focus_zero"] == 2  # both have form == lemma


def test_evaluate_dataset_errors_and_skip(lemmatizers):
    lemmatizer, greedy_lemmatizer = lemmatizers
    result = evaluate_dataset(parse(CONLLU_ERRORS), lemmatizer, greedy_lemmatizer, "en")

    assert result["total"] == 1  # "_" lemma token skipped
    assert result["zero"] == 0  # OOV form != gold lemma
    assert len(result["errors"]) == 1  # OOV mismatch recorded
    assert result["errors"][0][0] == "qwxztest"  # (form, gold, candidate, greedy)


def test_main_writes_results(tmp_path):
    clean = tmp_path / "UD"
    clean.mkdir()
    (clean / "en_test.conllu").write_text(CONLLU, encoding="utf-8")
    results = tmp_path / "results"

    # run twice: the second call exercises the results-folder reset branch
    evaluate_simplemma.main(clean, results)
    evaluate_simplemma.main(clean, results)

    summary = (results / "results_summary.csv").read_text()
    assert "dataset" in summary  # header row
    assert "en_test" in summary  # one data row
    assert (results / "en_test.csv").exists()  # per-dataset errors file


def test_main_requires_data(tmp_path):
    with pytest.raises(Exception, match="doesn't seem like data"):
        evaluate_simplemma.main(tmp_path / "missing", tmp_path / "results")
