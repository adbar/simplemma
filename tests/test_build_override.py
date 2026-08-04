import logging
import sys

from simplemma.strategies.dictionaries import dictionary_factory
from training import build_override as bo
from training import dictionary_builder, eval_gate

from .conftest import conllu as _conllu


def _collect(tmp_path, lang: str, texts: list[str]):
    paths = []
    for i, text in enumerate(texts):
        path = tmp_path / f"{lang}_tb{i}-ud-train.conllu"
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return bo.collect_candidates(paths, lang)


def test_collect_candidates_all_pos_with_pos_counts(tmp_path):
    per_tb, pos = _collect(
        tmp_path,
        "es",
        [_conllu([[(1, "el", "el", "PRON"), (2, "corre", "correr", "VERB")]])],
    )
    assert per_tb == [{"el": {"el": 1}, "corre": {"correr": 1}}]
    assert pos["el"] == {"PRON": 1} and pos["corre"] == {"VERB": 1}


def test_collect_candidates_inherits_canon(tmp_path):
    """The mined lemma is canonicalized for lang (via iter_word_tokens), so
    the override ships in the dict's key space -- the ar dead-key bug came
    from doing this by hand. Here a vocalized ar gold lemma is folded."""
    per_tb, _ = _collect(tmp_path, "ar", ["1\tب\tبِ\tADP\t_\t_\t0\troot\t_\t_\n\n"])
    assert per_tb == [{"ب": {"ب": 1}}]  # بِ -> ب


def test_collect_candidates_lowercases_sentence_initial_only(tmp_path):
    per_tb, _ = _collect(
        tmp_path,
        "es",
        [
            _conllu(
                [
                    [(1, "El", "el", "PRON")],  # sentence-initial: lowercased
                    [(1, "corre", "correr", "VERB"), (2, "El", "el", "PRON")],
                ]
            )
        ],
    )
    assert per_tb[0]["el"] == {"el": 1} and per_tb[0]["El"] == {"el": 1}


def test_collect_candidates_skips_underscore_lemma_and_symbols(tmp_path):
    per_tb, _ = _collect(
        tmp_path,
        "es",
        [_conllu([[(1, "x", "_", "PRON"), (2, ":", "на", "PUNCT")]])],
    )
    assert per_tb == [{}]  # underscore lemma skipped; letterless form skipped


def test_collect_candidates_skips_multiword_tokens(tmp_path):
    """A multiword-token span row (id like '1-2') must not be treated as a token."""
    text = (
        "1-2\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tde\tde\tADP\t_\t_\t0\troot\t_\t_\n"
        "2\tel\tel\tDET\t_\t_\t0\troot\t_\t_\n\n"
    )
    per_tb, _ = _collect(tmp_path, "es", [text])
    assert per_tb == [{"de": {"de": 1}, "el": {"el": 1}}]


def _resolve(counts, pos=None):
    from collections import Counter

    counts = {f: Counter(c) for f, c in counts.items()}
    if pos is None:
        pos = {f: Counter({"PRON": 1}) for f in counts}
    return bo.resolve_overrides([counts], pos)


def test_resolve_overrides_keeps_strong_majority():
    assert _resolve({"el": {"el": 9, "ella": 1}}) == {"el": "el"}


def test_resolve_overrides_drops_low_count():
    assert _resolve({"rare": {"rare": 2}}) == {}


def test_resolve_overrides_drops_low_agreement():
    # majority lemma only 60% agreement: below the closed-class 90% bar
    assert _resolve({"se": {"se": 6, "el": 4}}) == {}


def test_resolve_overrides_open_class_needs_more_evidence():
    from collections import Counter

    pooled = {"corre": {"correr": 4}}  # enough for closed (>=3), not open (>=5)
    pos = {"corre": Counter({"VERB": 1})}
    assert _resolve(pooled, pos=pos) == {}
    pooled = {"corre": {"correr": 5}}
    assert _resolve(pooled, pos=pos) == {"corre": "correr"}


def test_resolve_overrides_per_treebank_veto():
    """A treebank attesting the form >=3 times with a DIFFERENT majority
    vetoes the pooled winner (the la 'esse' / fr 'se'->soi convention split)."""
    from collections import Counter

    agreeing = {"esse": Counter({"esse": 30})}
    dissenting = {"esse": Counter({"sum": 3})}  # pooled: 91% agreement
    assert (
        bo.resolve_overrides([agreeing, dissenting], {"esse": Counter({"AUX": 1})})
        == {}
    )
    # under the veto threshold, the dissent does not count
    dissenting_weak = {"esse": Counter({"sum": 2})}
    assert bo.resolve_overrides(
        [agreeing, dissenting_weak], {"esse": Counter({"AUX": 1})}
    ) == {"esse": "esse"}


def test_main_end_to_end_ships_on_pass(tmp_path, monkeypatch):
    """main(): mine train splits -> merge with existing -> gate vs the
    composed baseline -> --in-place promotes the reviewed file."""
    # shipped zz dict knows corre->correr; corres is the minable delta
    (tmp_path / "zz.txt").write_text("correr\tcorre\n", encoding="utf-8")
    dictionary_builder._build_dictionary(
        "zz", listpath=str(tmp_path), filepath=str(tmp_path / "zz.plzma")
    )
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset({"zz"}))

    splits = tmp_path / "splits"
    splits.mkdir()
    train = _conllu([[(1, "corres", "correr", "VERB")]] * 5)  # open class >=5
    test = _conllu([[(1, "corres", "correr", "VERB"), (2, "corre", "correr", "VERB")]])
    (splits / "zz_x-ud-train.conllu").write_text(train, encoding="utf-8")
    (splits / "zz_x-ud-test.conllu").write_text(test, encoding="utf-8")
    monkeypatch.setattr(eval_gate, "UD_SPLITS", splits)

    overrides = tmp_path / "overrides"
    overrides.mkdir()
    monkeypatch.setattr(bo, "OVERRIDES_DIR", overrides)
    monkeypatch.setattr(bo, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(dictionary_builder, "OVERRIDES_DIR", overrides)
    monkeypatch.setattr(sys, "argv", ["build_override", "zz", "--in-place"])

    bo.main()  # a gate FAIL or missing treebank would sys.exit

    expected = "correr\tcorres\n"
    assert (tmp_path / "output" / "zz.tsv").read_text(encoding="utf-8") == expected
    assert (overrides / "zz.tsv").read_text(encoding="utf-8") == expected


def test_merge_with_existing_keeps_reviewed_entries(tmp_path):
    (tmp_path / "es.tsv").write_text("ser\tes\n", encoding="utf-8")
    merged, added = bo.merge_with_existing(
        {"es": "estar", "la": "la", "top hat": "top hat"}, "es", tmp_path
    )
    assert merged == {"es": "ser", "la": "la"}  # existing wins; spaced skipped
    assert added == 1


def test_merge_with_existing_warns_on_candidate_collision(tmp_path, caplog):
    """Two mined forms folding to one canonical key with different lemmas:
    first wins, but LOUDLY (_layer_entries raises on this in a reviewed file)."""
    candidates = {"שָׁלוֹם": "לום", "שלום": "אחר"}  # both fold to שלום
    with caplog.at_level(logging.WARNING, logger=bo.log.name):
        merged, added = bo.merge_with_existing(candidates, "he", tmp_path)
    assert merged == {"שלום": "לום"}
    assert added == 1
    assert "collide" in caplog.text
