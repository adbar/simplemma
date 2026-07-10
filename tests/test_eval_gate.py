import sys

import pytest

from training import eval_gate


def _conllu(rows: list[tuple[int, str, str]]) -> str:
    lines = [
        "\t".join([str(i), form, lemma, "X", "_", "_", "0", "root", "_", "_"])
        for i, form, lemma in rows
    ]
    return "\n".join(lines) + "\n\n"


def test_discover_test_treebanks_matches_language_prefix(tmp_path):
    (tmp_path / "ro_rrt-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "ro_simonero-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "ro_rrt-ud-train.conllu").write_text(
        "", encoding="utf-8"
    )  # not a test split
    (tmp_path / "pl_pdb-ud-test.conllu").write_text(
        "", encoding="utf-8"
    )  # different lang

    found = eval_gate.discover_test_treebanks("ro", ud_splits=tmp_path)
    assert [p.name for p in found] == [
        "ro_rrt-ud-test.conllu",
        "ro_simonero-ud-test.conllu",
    ]


def test_discover_test_treebanks_none_found(tmp_path):
    assert eval_gate.discover_test_treebanks("xx", ud_splits=tmp_path) == []


def test_discover_test_treebanks_handles_lang_prefix_overrides(tmp_path):
    """UD names some files by dataset prefix, not simplemma's language code
    (both Norwegian datasets are 'no_*'; North Sami is 'sme_giella-*') -- a
    naive first-underscore split misses them and can't tell Bokmål from
    Nynorsk (both would collapse to 'no')."""
    (tmp_path / "no_bokmaal-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "no_nynorsk-ud-test.conllu").write_text("", encoding="utf-8")
    (tmp_path / "sme_giella-ud-test.conllu").write_text("", encoding="utf-8")

    assert [
        p.name for p in eval_gate.discover_test_treebanks("nb", ud_splits=tmp_path)
    ] == ["no_bokmaal-ud-test.conllu"]
    assert [
        p.name for p in eval_gate.discover_test_treebanks("nn", ud_splits=tmp_path)
    ] == ["no_nynorsk-ud-test.conllu"]
    assert [
        p.name for p in eval_gate.discover_test_treebanks("se", ud_splits=tmp_path)
    ] == ["sme_giella-ud-test.conllu"]
    # and the raw prefixes ("no", "sme") must NOT themselves match
    assert eval_gate.discover_test_treebanks("no", ud_splits=tmp_path) == []
    assert eval_gate.discover_test_treebanks("sme", ud_splits=tmp_path) == []


def test_gate_raises_when_no_treebank_found(tmp_path):
    """A gate that silently checks nothing must not look like it passed."""
    with pytest.raises(ValueError, match="no UD test treebank"):
        eval_gate.gate("xx", {}, {}, ud_splits=tmp_path)


def test_gate_passes_when_candidate_strictly_improves(tmp_path):
    (tmp_path / "en_x-ud-test.conllu").write_text(
        _conllu([(1, "dogs", "dog"), (2, "cats", "cat")]), encoding="utf-8"
    )
    baseline = {"dogs": "dog"}  # misses "cats"
    candidate = {"dogs": "dog", "cats": "cat"}
    results = eval_gate.gate("en", baseline, candidate, ud_splits=tmp_path)
    assert len(results) == 1
    assert results[0].passed()
    assert results[0].token_delta > 0


def test_gate_fails_when_candidate_regresses(tmp_path):
    (tmp_path / "en_x-ud-test.conllu").write_text(
        _conllu([(1, "dogs", "dog"), (2, "cats", "cat")]), encoding="utf-8"
    )
    baseline = {"dogs": "dog", "cats": "cat"}
    candidate = {"dogs": "dog"}  # regressed: dropped "cats"
    results = eval_gate.gate("en", baseline, candidate, ud_splits=tmp_path)
    assert not results[0].passed()
    assert results[0].token_delta < 0


def test_gate_checks_every_discovered_treebank_independently(tmp_path):
    """Cross-treebank: one treebank improving must not mask another regressing."""
    (tmp_path / "en_a-ud-test.conllu").write_text(
        _conllu([(1, "dogs", "dog")]), encoding="utf-8"
    )
    (tmp_path / "en_b-ud-test.conllu").write_text(
        _conllu([(1, "cats", "cat")]), encoding="utf-8"
    )
    baseline = {"dogs": "dog", "cats": "cat"}
    candidate = {"dogs": "dog"}  # fine on treebank a, regresses on treebank b
    results = eval_gate.gate("en", baseline, candidate, ud_splits=tmp_path)
    by_name = {r.treebank: r for r in results}
    assert by_name["en_a-ud-test"].passed()
    assert not by_name["en_b-ud-test"].passed()


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
    (tmp_path / "en_x-ud-test.conllu").write_text(
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
    (tmp_path / "en_x-ud-test.conllu").write_text(
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
