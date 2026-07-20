from collections import Counter

from training import build_override as bo

from .conftest import conllu as _conllu


def test_collect_candidates_filters_to_closed_class(tmp_path):
    path = tmp_path / "train.conllu"
    path.write_text(
        _conllu(
            [
                [
                    (1, "el", "el", "PRON"),
                    (2, "corre", "correr", "VERB"),  # open class: excluded
                ]
            ]
        ),
        encoding="utf-8",
    )
    candidates = bo.collect_candidates(path, "es")
    assert candidates == {"el": {"el": 1}}


def test_collect_candidates_inherits_canon(tmp_path):
    """The mined lemma is canonicalized for lang (via iter_word_tokens), so
    the override ships in the dict's key space -- the ar dead-key bug came
    from doing this by hand. Here a vocalized ar gold lemma is folded."""
    path = tmp_path / "train.conllu"
    path.write_text("1\tب\tبِ\tADP\t_\t_\t0\troot\t_\t_\n\n", encoding="utf-8")
    assert bo.collect_candidates(path, "ar") == {"ب": {"ب": 1}}  # بِ -> ب


def test_collect_candidates_lowercases_sentence_initial_only(tmp_path):
    path = tmp_path / "train.conllu"
    path.write_text(
        _conllu(
            [
                [(1, "El", "el", "PRON")],  # sentence-initial: lowercased
                [
                    (1, "corre", "correr", "VERB"),
                    (2, "El", "el", "PRON"),
                ],  # not initial
            ]
        ),
        encoding="utf-8",
    )
    candidates = bo.collect_candidates(path, "es")
    assert candidates == {"el": {"el": 1}, "El": {"el": 1}}


def test_collect_candidates_skips_underscore_lemma(tmp_path):
    path = tmp_path / "train.conllu"
    path.write_text(
        _conllu([[(1, "x", "_", "PRON")]]),
        encoding="utf-8",
    )
    assert bo.collect_candidates(path, "es") == {}


def test_collect_candidates_skips_multiword_tokens(tmp_path):
    """A multiword-token span row (id like '1-2') must not be treated as a token."""
    path = tmp_path / "train.conllu"
    text = (
        "1-2\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tde\tde\tADP\t_\t_\t0\troot\t_\t_\n"
        "2\tel\tel\tDET\t_\t_\t0\troot\t_\t_\n\n"
    )
    path.write_text(text, encoding="utf-8")
    candidates = bo.collect_candidates(path, "es")
    assert candidates == {"de": {"de": 1}, "el": {"el": 1}}


def test_resolve_overrides_keeps_strong_majority():
    candidates = {"el": Counter({"el": 9, "ella": 1})}
    overrides, stats = bo.resolve_overrides(candidates, min_count=3, min_agreement=0.90)
    assert overrides == {"el": "el"}
    assert stats["kept"] == 1
    assert stats["dropped_low_agreement"] == 0


def test_resolve_overrides_drops_low_count():
    candidates = {"rare": Counter({"rare": 2})}
    overrides, stats = bo.resolve_overrides(candidates, min_count=3, min_agreement=0.90)
    assert overrides == {}
    assert stats["dropped_low_count"] == 1


def test_resolve_overrides_drops_low_agreement():
    # majority lemma only 60% agreement: below the 90% bar
    candidates = {"se": Counter({"se": 6, "el": 4})}
    overrides, stats = bo.resolve_overrides(candidates, min_count=3, min_agreement=0.90)
    assert overrides == {}
    assert stats["dropped_low_agreement"] == 1


def test_resolve_overrides_picks_majority_not_first():
    candidates = {"la": Counter({"el": 1, "la": 19})}
    overrides, stats = bo.resolve_overrides(candidates, min_count=3, min_agreement=0.90)
    assert overrides == {"la": "la"}


def test_resolve_overrides_drops_symbol_forms():
    # treebank annotation noise: a symbol "form" would become a runtime bug
    # (bg ":" -> "на"); closed-class words carry letters.
    candidates = {
        ":": Counter({"на": 10}),
        "&": Counter({"&": 10}),
        "d'": Counter({"de": 10}),  # elision WITH letters: kept
    }
    overrides, stats = bo.resolve_overrides(candidates, min_count=3, min_agreement=0.90)
    assert overrides == {"d'": "de"}


def test_main_end_to_end(tmp_path, monkeypatch):
    train_path = tmp_path / "train.conllu"
    rows = [[(1, "el", "el", "PRON")] for _ in range(5)]
    rows.append([(1, "corre", "correr", "VERB")])  # open class: excluded
    train_path.write_text(_conllu(rows), encoding="utf-8")
    output_path = tmp_path / "es_override.tsv"

    monkeypatch.setattr(
        "sys.argv",
        ["build_override.py", "es", str(train_path), str(output_path)],
    )
    bo.main()

    assert output_path.read_text(encoding="utf-8") == "el\tel\n"
