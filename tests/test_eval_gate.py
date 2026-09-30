import logging

import pytest

from training import eval_gate, ud_conllu
from training.eval_gate import (
    FixedDictionaryFactory,
    accuracy,
    build_lemmatizer,
    gold_types,
    load_gold_tokens,
)

from .conftest import conllu


def _conllu(rows: list[tuple[int, str, str]]) -> str:
    """One-sentence wrapper over the shared conftest builder."""
    return conllu([rows])


def test_discover_test_treebanks_matches_language_prefix(tmp_path):
    (tmp_path / "ro_rrt-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "ro_simonero-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "ro_rrt-ud-train.conllu").write_text("", encoding="utf-8")
    (tmp_path / "pl_pdb-ud-test.conllu").write_text("", encoding="utf-8")

    found = ud_conllu.discover_treebanks("ro", "test", ud_splits=tmp_path)
    assert [p.name for p in found] == [
        "ro_rrt-ud-test.conllu",
        "ro_simonero-ud-test.conllu",
    ]


def test_discover_test_treebanks_none_found(tmp_path):
    assert ud_conllu.discover_treebanks("xx", "test", ud_splits=tmp_path) == []


def test_discover_test_treebanks_handles_lang_prefix_overrides(tmp_path):
    """UD names both Norwegian datasets 'no_*', so a prefix split cannot tell nb from nn."""
    (tmp_path / "no_bokmaal-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "no_nynorsk-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "sme_giella-ud-test.conllu").write_text("", encoding="utf-8")

    assert [
        p.name for p in ud_conllu.discover_treebanks("nb", "test", ud_splits=tmp_path)
    ] == ["no_bokmaal-ud-test.conllu"]
    assert [
        p.name for p in ud_conllu.discover_treebanks("nn", "test", ud_splits=tmp_path)
    ] == ["no_nynorsk-ud-test.conllu"]
    assert [
        p.name for p in ud_conllu.discover_treebanks("se", "test", ud_splits=tmp_path)
    ] == ["sme_giella-ud-test.conllu"]
    assert ud_conllu.discover_treebanks("no", "test", ud_splits=tmp_path) == []
    assert ud_conllu.discover_treebanks("sme", "test", ud_splits=tmp_path) == []


def test_gate_raises_when_no_treebank_found(tmp_path):
    """A gate that silently checks nothing must not look like it passed."""
    with pytest.raises(ValueError, match="no UD treebank of any split"):
        eval_gate.gate("xx", {}, {}, ud_splits=tmp_path)


def test_gate_prefers_train_over_reported_splits(tmp_path):
    """The gate is model selection, so it reads train even when dev and test exist."""
    for split, row in (("train", "dogs"), ("dev", "cats"), ("test", "cows")):
        (tmp_path / f"en_x-ud-{split}.conllu").write_text(
            _conllu([(1, row, row[:-1])]), encoding="utf-8"
        )
    results = eval_gate.gate("en", {}, {"dogs": "dog"}, ud_splits=tmp_path)
    assert [r.treebank for r in results] == ["en_x-ud-train"]


def test_gate_falls_back_to_a_reported_split_and_warns(tmp_path, caplog):
    """Without a train split the gate uses a published split and warns."""
    (tmp_path / "en_x-ud-dev.conllu").write_text(
        _conllu([(1, "dogs", "dog")]), encoding="utf-8"
    )
    with caplog.at_level(logging.WARNING, logger=eval_gate.log.name):
        results = eval_gate.gate("en", {}, {"dogs": "dog"}, ud_splits=tmp_path)
    assert [r.treebank for r in results] == ["en_x-ud-dev"]
    assert "no UD train split" in caplog.text and "DEV" in caplog.text


def test_gate_resolves_split_per_treebank(tmp_path, caplog):
    """A test-only sibling treebank stays gated next to one with a train split."""
    (tmp_path / "en_x-ud-train.conllu").write_text(
        _conllu([(1, "dogs", "dog")]), encoding="utf-8"
    )
    (tmp_path / "en_pud-ud-test.conllu").write_text(
        _conllu([(1, "cats", "cat")]), encoding="utf-8"
    )
    with caplog.at_level(logging.WARNING, logger=eval_gate.log.name):
        results = eval_gate.gate("en", {}, {"dogs": "dog"}, ud_splits=tmp_path)
    assert [r.treebank for r in results] == ["en_pud-ud-test", "en_x-ud-train"]
    assert "en_pud has no UD train split" in caplog.text and "TEST" in caplog.text


def test_gate_falls_back_all_the_way_to_test(tmp_path, caplog):
    """A test-only treebank exercises the last fallback level."""
    (tmp_path / "en_x-ud-test.conllu").write_text(
        _conllu([(1, "dogs", "dog")]), encoding="utf-8"
    )
    with caplog.at_level(logging.WARNING, logger=eval_gate.log.name):
        results = eval_gate.gate("en", {}, {"dogs": "dog"}, ud_splits=tmp_path)
    assert [r.treebank for r in results] == ["en_x-ud-test"]
    assert "TEST" in caplog.text


def test_gate_passes_when_candidate_strictly_improves(tmp_path):
    (tmp_path / "en_x-ud-train.conllu").write_text(
        _conllu([(1, "dogs", "dog"), (2, "cats", "cat")]), encoding="utf-8"
    )
    baseline = {"dogs": "dog"}
    candidate = {"dogs": "dog", "cats": "cat"}
    results = eval_gate.gate("en", baseline, candidate, ud_splits=tmp_path)
    assert len(results) == 1
    assert results[0].passed()
    assert results[0].token_delta > 0


def test_gate_fails_when_candidate_regresses(tmp_path):
    (tmp_path / "en_x-ud-train.conllu").write_text(
        _conllu([(1, "dogs", "dog"), (2, "cats", "cat")]), encoding="utf-8"
    )
    baseline = {"dogs": "dog", "cats": "cat"}
    candidate = {"dogs": "dog"}
    results = eval_gate.gate("en", baseline, candidate, ud_splits=tmp_path)
    assert not results[0].passed()
    assert results[0].token_delta < 0


def test_gate_checks_every_discovered_treebank_independently(tmp_path):
    """Cross-treebank: one treebank improving must not mask another regressing."""
    (tmp_path / "en_a-ud-train.conllu").write_text(
        _conllu([(1, "dogs", "dog")]), encoding="utf-8"
    )
    (tmp_path / "en_b-ud-train.conllu").write_text(
        _conllu([(1, "cats", "cat")]), encoding="utf-8"
    )
    baseline = {"dogs": "dog", "cats": "cat"}
    candidate = {"dogs": "dog"}
    results = eval_gate.gate("en", baseline, candidate, ud_splits=tmp_path)
    by_name = {r.treebank: r for r in results}
    assert by_name["en_a-ud-train"].passed()
    assert not by_name["en_b-ud-train"].passed()


def test_treebank_result_epsilon_tolerance():
    result = eval_gate.TreebankResult(
        treebank="t",
        baseline_token=0.900,
        candidate_token=0.8995,  # -0.05pp: within a 0.1pp tolerance
        baseline_type=0.900,
        candidate_type=0.900,
        n_tokens=1000,
        n_types=100,
    )
    assert result.passed(epsilon=0.001)
    assert not result.passed(epsilon=0.0001)


def test_treebank_result_deltas():
    result = eval_gate.TreebankResult(
        treebank="t",
        baseline_token=0.80,
        candidate_token=0.85,
        baseline_type=0.70,
        candidate_type=0.65,
        n_tokens=10,
        n_types=10,
    )
    assert result.token_delta == pytest.approx(0.05)
    assert result.type_delta == pytest.approx(-0.05)


def score_type(strategy, lang, gold_tokens):
    return accuracy(strategy, lang, gold_types(gold_tokens))


def test_fixed_dictionary_factory_serves_the_mapping():
    factory = FixedDictionaryFactory({"dogs": "dog"})
    assert factory.get_dictionary("en")["dogs"] == "dog"


def test_token_accuracy_perfect_dictionary(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        conllu([[(1, "dogs", "dog"), (2, "cats", "cat")]]), encoding="utf-8"
    )
    acc, n = accuracy(
        build_lemmatizer({"dogs": "dog", "cats": "cat"}),
        "en",
        load_gold_tokens(path, "en"),
    )
    assert acc == 1.0
    assert n == 2


def test_token_accuracy_folds_curly_apostrophes():
    """Gold forms are folded like Lemmatizer does, so a curly form hits its straight key."""
    acc, n = accuracy(build_lemmatizer({"l'uomo": "uomo"}), "it", [("l’uomo", "uomo")])
    assert (acc, n) == (1.0, 1)
    # identity fallback keeps the input glyph, as Lemmatizer does
    assert accuracy(build_lemmatizer({}), "tr", [("X’ye", "X’ye")]) == (1.0, 1)


def test_token_accuracy_identity_fallback_on_miss(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(conllu([[(1, "run", "run")]]), encoding="utf-8")
    acc, n = accuracy(build_lemmatizer({}), "en", load_gold_tokens(path, "en"))
    assert acc == 1.0
    assert n == 1


def test_token_accuracy_skips_underscore_lemma_and_lowercases_initial(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        conllu([[(1, "Dogs", "dog"), (2, "x", "_")]]),
        encoding="utf-8",
    )
    acc, n = accuracy(
        build_lemmatizer({"dogs": "dog"}), "en", load_gold_tokens(path, "en")
    )
    assert n == 1
    assert acc == 1.0


def test_token_accuracy_skips_multiword_tokens(tmp_path):
    path = tmp_path / "test.conllu"
    text = (
        "1-2\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tde\tde\tX\t_\t_\t0\troot\t_\t_\n"
        "2\tel\tel\tX\t_\t_\t0\troot\t_\t_\n\n"
    )
    path.write_text(text, encoding="utf-8")
    acc, n = accuracy(
        build_lemmatizer({"de": "de", "el": "el"}), "es", load_gold_tokens(path, "es")
    )
    assert n == 2


def test_token_accuracy_is_frequency_weighted(tmp_path):
    path = tmp_path / "test.conllu"
    rows = [[(1, "common", "commonlemma")] for _ in range(3)] + [
        [(1, "rare", "rarelemma")]
    ]
    path.write_text(conllu(rows), encoding="utf-8")
    mapping = {"common": "commonlemma", "rare": "WRONG"}
    acc, n = accuracy(build_lemmatizer(mapping), "en", load_gold_tokens(path, "en"))
    assert n == 4
    assert acc == 0.75


def test_type_accuracy_weights_repeated_form_once(tmp_path):
    path = tmp_path / "test.conllu"
    rows = [[(1, "common", "commonlemma")] for _ in range(3)] + [
        [(1, "rare", "rarelemma")]
    ]
    path.write_text(conllu(rows), encoding="utf-8")
    mapping = {"common": "commonlemma", "rare": "WRONG"}
    acc, n = score_type(build_lemmatizer(mapping), "en", load_gold_tokens(path, "en"))
    assert n == 2
    assert acc == 0.5


def test_type_accuracy_uses_majority_gold_for_ambiguous_form(tmp_path):
    """A form with inconsistent gold lemmas is scored against its majority gold lemma."""
    path = tmp_path / "test.conllu"
    rows = [[(1, "bank", "bank_river")] for _ in range(3)] + [
        [(1, "bank", "bank_money")] for _ in range(1)
    ]
    path.write_text(conllu(rows), encoding="utf-8")
    acc, n = score_type(
        build_lemmatizer({"bank": "bank_river"}), "en", load_gold_tokens(path, "en")
    )
    assert n == 1
    assert acc == 1.0


def test_type_and_token_agree_when_no_repeats(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(
        conllu([[(1, "a", "a"), (2, "b", "b"), (3, "c", "WRONG")]]),
        encoding="utf-8",
    )
    mapping = {"a": "a", "b": "b", "c": "c"}
    gold_tokens = load_gold_tokens(path, "en")
    strategy = build_lemmatizer(mapping)
    tok_acc, tok_n = accuracy(strategy, "en", gold_tokens)
    typ_acc, typ_n = score_type(strategy, "en", gold_tokens)
    assert tok_acc == typ_acc
    assert tok_n == typ_n


def test_real_affix_chain_is_exercised_not_just_dict_lookup(tmp_path):
    """talossa is not a dict key but derives from talo via the fi -ssa rule."""
    path = tmp_path / "test.conllu"
    path.write_text(conllu([[(1, "talossa", "talo")]]), encoding="utf-8")
    acc, n = accuracy(
        build_lemmatizer({"talo": "talo"}), "fi", load_gold_tokens(path, "fi")
    )
    assert n == 1
    assert acc == 1.0


def test_load_gold_tokens_canonicalizes_gold_lemma_for_ar(tmp_path):
    """ar gold lemmas are vocalized and the dict is not, so gold is canonicalized."""
    path = tmp_path / "test.conllu"
    path.write_text(conllu([[(1, "كتاب", "كِتَاب")]]), encoding="utf-8")
    ((form, gold),) = load_gold_tokens(path, "ar")
    assert gold == "كتاب"
    acc, n = accuracy(
        build_lemmatizer({"كتاب": "كتاب"}), "ar", load_gold_tokens(path, "ar")
    )
    assert acc == 1.0


def test_load_gold_tokens_leaves_other_langs_unaffected(tmp_path):
    path = tmp_path / "test.conllu"
    path.write_text(conllu([[(1, "dogs", "dog")]]), encoding="utf-8")
    ((form, gold),) = load_gold_tokens(path, "en")
    assert gold == "dog"
