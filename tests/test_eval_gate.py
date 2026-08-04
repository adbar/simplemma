import logging
import sys

import pytest

from training import eval_gate

from .conftest import conllu


def _conllu(rows: list[tuple[int, str, str]]) -> str:
    """One-sentence wrapper over the shared conftest builder."""
    return conllu([rows])


def test_discover_test_treebanks_matches_language_prefix(tmp_path):
    (tmp_path / "ro_rrt-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "ro_simonero-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "ro_rrt-ud-train.conllu").write_text(
        "", encoding="utf-8"
    )  # not a test split
    (tmp_path / "pl_pdb-ud-test.conllu").write_text(
        "", encoding="utf-8"
    )  # different lang

    found = eval_gate.discover_treebanks("ro", "test", ud_splits=tmp_path)
    assert [p.name for p in found] == [
        "ro_rrt-ud-test.conllu",
        "ro_simonero-ud-test.conllu",
    ]


def test_discover_test_treebanks_none_found(tmp_path):
    assert eval_gate.discover_treebanks("xx", "test", ud_splits=tmp_path) == []


def test_discover_test_treebanks_handles_lang_prefix_overrides(tmp_path):
    """UD names some files by dataset prefix, not simplemma's language code (both
    Norwegian datasets are 'no_*') -- a naive first-underscore split can't tell
    Bokmål from Nynorsk."""
    (tmp_path / "no_bokmaal-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "no_nynorsk-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "sme_giella-ud-test.conllu").write_text("", encoding="utf-8")

    assert [
        p.name for p in eval_gate.discover_treebanks("nb", "test", ud_splits=tmp_path)
    ] == ["no_bokmaal-ud-test.conllu"]
    assert [
        p.name for p in eval_gate.discover_treebanks("nn", "test", ud_splits=tmp_path)
    ] == ["no_nynorsk-ud-test.conllu"]
    assert [
        p.name for p in eval_gate.discover_treebanks("se", "test", ud_splits=tmp_path)
    ] == ["sme_giella-ud-test.conllu"]
    # and the raw prefixes ("no", "sme") must NOT themselves match
    assert eval_gate.discover_treebanks("no", "test", ud_splits=tmp_path) == []
    assert eval_gate.discover_treebanks("sme", "test", ud_splits=tmp_path) == []


def test_gate_raises_when_no_treebank_found(tmp_path):
    """A gate that silently checks nothing must not look like it passed."""
    with pytest.raises(ValueError, match="no UD treebank of any split"):
        eval_gate.gate("xx", {}, {}, ud_splits=tmp_path)


def test_gate_prefers_train_over_reported_splits(tmp_path):
    """Split discipline: the gate is model selection, so it must read train --
    the only unpublished split -- even with dev and test sitting next to it."""
    for split, row in (("train", "dogs"), ("dev", "cats"), ("test", "cows")):
        (tmp_path / f"en_x-ud-{split}.conllu").write_text(
            _conllu([(1, row, row[:-1])]), encoding="utf-8"
        )
    results = eval_gate.gate("en", {}, {"dogs": "dog"}, ud_splits=tmp_path)
    assert [r.treebank for r in results] == ["en_x-ud-train"]


def test_gate_falls_back_to_a_reported_split_and_warns(tmp_path, caplog):
    """A language with no train split must still be gated, on a published
    split, but the caller has to be told the number is then selected."""
    (tmp_path / "en_x-ud-dev.conllu").write_text(
        _conllu([(1, "dogs", "dog")]), encoding="utf-8"
    )
    with caplog.at_level(logging.WARNING, logger=eval_gate.log.name):
        results = eval_gate.gate("en", {}, {"dogs": "dog"}, ud_splits=tmp_path)
    assert [r.treebank for r in results] == ["en_x-ud-dev"]
    assert "no UD train split" in caplog.text and "DEV" in caplog.text


def test_gate_resolves_split_per_treebank(tmp_path, caplog):
    """A test-only sibling (*_pud) keeps gate coverage next to a train-having
    treebank -- per-language split resolution would silently drop it."""
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
    """A test-only treebank (tl) exercises the last fallback level."""
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
    baseline = {"dogs": "dog"}  # misses "cats"
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
    candidate = {"dogs": "dog"}  # regressed: dropped "cats"
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
    candidate = {"dogs": "dog"}  # fine on treebank a, regresses on treebank b
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


def test_main_cli_exits_zero_on_pass(tmp_path, monkeypatch):
    (tmp_path / "en_x-ud-train.conllu").write_text(
        _conllu([(1, "dogs", "dog"), (2, "cats", "cat")]), encoding="utf-8"
    )
    baseline_path = tmp_path / "baseline.tsv"
    candidate_path = tmp_path / "candidate.tsv"
    baseline_path.write_text("dog\tdogs\n", encoding="utf-8")  # misses "cats"
    candidate_path.write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")  # improved

    monkeypatch.setattr(eval_gate, "UD_SPLITS", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["eval_gate.py", "en", str(baseline_path), str(candidate_path)],
    )
    eval_gate.main()  # must not raise / exit


def test_main_cli_exits_nonzero_on_regression(tmp_path, monkeypatch):
    (tmp_path / "en_x-ud-train.conllu").write_text(
        _conllu([(1, "dogs", "dog"), (2, "cats", "cat")]), encoding="utf-8"
    )
    baseline_path = tmp_path / "baseline.tsv"
    candidate_path = tmp_path / "candidate.tsv"
    baseline_path.write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    candidate_path.write_text("dog\tdogs\n", encoding="utf-8")  # regressed

    monkeypatch.setattr(eval_gate, "UD_SPLITS", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["eval_gate.py", "en", str(baseline_path), str(candidate_path)],
    )
    with pytest.raises(SystemExit) as excinfo:
        eval_gate.main()
    assert excinfo.value.code == 1
