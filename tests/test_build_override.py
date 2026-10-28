import logging
import sys
from collections import Counter

import pytest

from training import build_override as bo
from training import ud_conllu

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
    """The mined lemma is canonicalized for lang, so overrides ship in the dict key space."""
    per_tb, _ = _collect(tmp_path, "ar", ["1\tب\tبِ\tADP\t_\t_\t0\troot\t_\t_\n\n"])
    assert per_tb == [{"ب": {"ب": 1}}]


def test_collect_candidates_lowercases_sentence_initial_only(tmp_path):
    per_tb, _ = _collect(
        tmp_path,
        "es",
        [
            _conllu(
                [
                    [(1, "El", "el", "PRON")],
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
    assert per_tb == [{}]  # underscore lemma and letterless form skipped


def test_collect_candidates_skips_multiword_tokens(tmp_path):
    text = (
        "1-2\tdel\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tde\tde\tADP\t_\t_\t0\troot\t_\t_\n"
        "2\tel\tel\tDET\t_\t_\t0\troot\t_\t_\n\n"
    )
    per_tb, _ = _collect(tmp_path, "es", [text])
    assert per_tb == [{"de": {"de": 1}, "el": {"el": 1}}]


def _resolve(counts, pos=None, current=lambda form: "?"):
    counts = {f: Counter(c) for f, c in counts.items()}
    if pos is None:
        pos = {f: Counter({"PRON": 1}) for f in counts}
    return bo.resolve_overrides([counts], pos, current)


def test_resolve_overrides_keeps_majority_beating_output():
    assert _resolve({"el": {"el": 9, "ella": 1}}) == {"el": "el"}


def test_resolve_overrides_drops_when_output_is_majority():
    assert _resolve({"el": {"el": 9}}, current=lambda form: "el") == {}


def test_resolve_overrides_drops_case_only_change():
    pos = {"Roma": Counter({"NOUN": 1})}
    assert _resolve({"Roma": {"roma": 9}}, pos, lambda form: form) == {}


def test_resolve_overrides_skips_cased_lemma_of_lowercase_form():
    pos = {"baron": Counter({"NOUN": 1})}
    assert _resolve({"baron": {"Baron": 9}}, pos) == {}


def test_resolve_overrides_veto_counts_lemma_up_to_case():
    per_tb = [
        {"es": Counter({"ser": 10})},
        {"es": Counter({"ser": 1, "Ser": 2, "estar": 2})},
    ]
    pos = {"es": Counter({"AUX": 1})}
    assert bo.resolve_overrides(per_tb, pos, lambda form: "estar") == {"es": "ser"}


def test_resolve_overrides_drops_low_count():
    assert _resolve({"rare": {"rare": 2}}) == {}


def test_resolve_overrides_skips_underscore_lemmas():
    assert _resolve({"keerde": {"terug_keren": 9}}) == {}
    assert _resolve({"a_b": {"a_b": 9}}) == {"a_b": "a_b"}


def test_resolve_overrides_skips_letterless_lemmas():
    assert _resolve({"1ste": {"1": 9}}) == {}


def test_resolve_overrides_counts_output_up_to_case():
    counts = {"se": {"se": 3, "el": 2}}
    assert _resolve(counts, current=lambda form: "El") == {}
    agreeing = {"se": Counter({"se": 6})}
    dissenting = {"se": Counter({"se": 1, "el": 3})}
    pos = {"se": Counter({"PRON": 1})}
    assert bo.resolve_overrides([agreeing, dissenting], pos, lambda f: "El") == {}


def test_resolve_overrides_agreement_floor():
    assert _resolve({"se": {"se": 5, "el": 4}}) == {}  # 56%
    assert _resolve({"se": {"se": 6, "el": 4}}) == {"se": "se"}  # 60%


def test_resolve_overrides_needs_gain_over_output():
    counts = {"se": {"se": 3, "el": 2}}
    assert _resolve(counts, current=lambda form: "el") == {}
    assert _resolve(counts) == {"se": "se"}


def test_resolve_overrides_open_class_needs_more_evidence():
    pooled = {"corre": {"correr": 4}}  # enough for closed (>=3), not open (>=5)
    pos = {"corre": Counter({"VERB": 1})}
    assert _resolve(pooled, pos=pos) == {}
    pooled = {"corre": {"correr": 5}}
    assert _resolve(pooled, pos=pos) == {"corre": "correr"}


def test_resolve_overrides_skips_excluded_tags():
    for tag in ("PROPN", "ADP", bo.PARTICIPLE):
        assert _resolve({"dicho": {"decir": 9}}, {"dicho": Counter({tag: 9})}) == {}


def test_resolve_overrides_per_treebank_veto():
    """A treebank with >=3 attestations where the output beats the winner vetoes it."""
    agreeing = {"esse": Counter({"esse": 30})}
    dissenting = {"esse": Counter({"sum": 3})}
    pos = {"esse": Counter({"AUX": 1})}
    assert bo.resolve_overrides([agreeing, dissenting], pos, lambda f: "sum") == {}
    # a dissent that the output does not share is no loss
    assert bo.resolve_overrides([agreeing, dissenting], pos, lambda f: "?") == {
        "esse": "esse"
    }
    # under the veto threshold, the dissent does not count
    dissenting_weak = {"esse": Counter({"sum": 2})}
    assert bo.resolve_overrides([agreeing, dissenting_weak], pos, lambda f: "sum") == {
        "esse": "esse"
    }


def test_main_end_to_end(tmp_path, monkeypatch, caplog):
    """main() mines train splits, merges, writes, and promotes with --in-place."""
    splits = tmp_path / "splits"
    splits.mkdir()
    train = _conllu([[(1, "corres", "correr", "VERB")]] * 5)  # open class needs >=5
    (splits / "zz_x-ud-train.conllu").write_text(train, encoding="utf-8")
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)

    overrides = tmp_path / "overrides"
    overrides.mkdir()
    (overrides / "zz.tsv").write_text("correr\tcorre\n", encoding="utf-8")
    monkeypatch.setattr(bo, "OVERRIDES_DIR", overrides)
    monkeypatch.setattr(bo, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(bo, "lemmatize", lambda token, lang: token)
    monkeypatch.setattr(sys, "argv", ["build_override", "zz", "--in-place"])

    with caplog.at_level(logging.INFO, logger=bo.log.name):
        bo.main()  # a missing treebank would sys.exit

    assert "1 new entries over 1 existing" in caplog.text
    expected = "correr\tcorre\ncorrer\tcorres\n"
    assert (tmp_path / "output" / "zz.tsv").read_text(encoding="utf-8") == expected
    assert (overrides / "zz.tsv").read_text(encoding="utf-8") == expected


def test_main_excludes_treebanks(tmp_path, monkeypatch):
    splits = tmp_path / "splits"
    splits.mkdir()
    kept = _conllu([[(1, "corres", "correr", "VERB")]] * 5)
    vetoing = _conllu([[(1, "corres", "corres", "VERB")]] * 5)
    (splits / "zz_x-ud-train.conllu").write_text(kept, encoding="utf-8")
    (splits / "zz_y-ud-train.conllu").write_text(vetoing, encoding="utf-8")
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)
    monkeypatch.setattr(bo, "OVERRIDES_DIR", tmp_path)
    monkeypatch.setattr(bo, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(bo, "lemmatize", lambda token, lang: token)
    monkeypatch.setattr(sys, "argv", ["build_override", "zz", "--exclude", "zz_y"])
    bo.main()
    assert (tmp_path / "output" / "zz.tsv").read_text(encoding="utf-8") == (
        "correr\tcorres\n"
    )


def test_main_passes_lang_to_lemmatize(tmp_path, monkeypatch):
    splits = tmp_path / "splits"
    splits.mkdir()
    train = _conllu([[(1, "corres", "correr", "VERB")]] * 5)
    (splits / "zz_x-ud-train.conllu").write_text(train, encoding="utf-8")
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)
    monkeypatch.setattr(bo, "OVERRIDES_DIR", tmp_path)
    monkeypatch.setattr(bo, "OUTPUT_DIR", tmp_path / "output")
    calls = []
    monkeypatch.setattr(
        bo, "lemmatize", lambda token, lang: calls.append((token, lang)) or token
    )
    monkeypatch.setattr(sys, "argv", ["build_override", "zz"])
    bo.main()
    assert calls == [("corres", "zz")]


def test_main_rejects_unknown_or_all_excluded(tmp_path, monkeypatch):
    splits = tmp_path / "splits"
    splits.mkdir()
    (splits / "zz_x-ud-train.conllu").write_text(_conllu([]), encoding="utf-8")
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)
    for excluded, message in (("zz_typo", "unknown treebanks"), ("zz_x", "all")):
        monkeypatch.setattr(
            sys, "argv", ["build_override", "zz", "--exclude", excluded]
        )
        with pytest.raises(SystemExit, match=message):
            bo.main()


def test_merge_with_existing_keeps_reviewed_entries(tmp_path):
    (tmp_path / "es.tsv").write_text("ser\tes\n", encoding="utf-8")
    merged, added = bo.merge_with_existing(
        {"es": "estar", "la": "la", "top hat": "top hat"}, "es", tmp_path
    )
    assert merged == {"es": "ser", "la": "la"}  # existing wins, spaced skipped
    assert added == 1


def test_merge_with_existing_skips_unshippable_pairs(tmp_path):
    """Merge output must survive read_pairs and _layer_entries."""
    candidates = {
        "c.q.": "casu quo",
        "basic\xadally": "basically",  # soft hyphen: Cf, read_pairs rejects
        "x": "",
        "la": "la",
    }
    merged, added = bo.merge_with_existing(candidates, "nl", tmp_path)
    assert merged == {"la": "la"}
    assert added == 1


def test_merge_with_existing_folds_nfc(tmp_path):
    """An NFD candidate lands on the NFC key, so it cannot collide with itself."""
    nfd, nfc = "cafe\u0301", "caf\u00e9"
    merged, _ = bo.merge_with_existing({nfd: nfd}, "fr", tmp_path)
    assert merged == {nfc: nfc}


def test_resolve_overrides_ties_are_insertion_order_independent():
    # POS tie AUX/VERB: stricter open-class bar applies whichever came first
    for pos_counts in ({"AUX": 3, "VERB": 3}, {"VERB": 3, "AUX": 3}):
        pooled = {"es": Counter({"ser": 4})}
        pos = {"es": Counter(pos_counts)}
        assert bo.resolve_overrides([pooled], pos, lambda f: "?") == {}
    # an evenly split treebank loses nothing: no veto
    agreeing = {"esse": Counter({"esse": 30})}
    for split_counts in ({"esse": 3, "sum": 3}, {"sum": 3, "esse": 3}):
        split_tb = {"esse": Counter(split_counts)}
        assert bo.resolve_overrides(
            [agreeing, split_tb], {"esse": Counter({"AUX": 1})}, lambda f: "sum"
        ) == {"esse": "esse"}


def test_collect_candidates_tags_participles(tmp_path):
    text = "1\tdicho\tdecir\tADJ\t_\tVerbForm=Part\t0\troot\t_\t_\n\n"
    _, pos = _collect(tmp_path, "es", [text])
    assert pos["dicho"] == {bo.PARTICIPLE: 1}


def test_report_contradictions_warns(tmp_path, caplog):
    (tmp_path / "es.tsv").write_text(
        "ser\tes\nel\tel\nRoma\tRoma\nJuan\tJuan\n", encoding="utf-8"
    )
    counts = {
        "es": Counter({"estar": 5}),
        "el": Counter({"el": 5}),
        "Roma": Counter({"roma": 5}),
        "Juan": Counter({"Juanito": 5}),
    }
    pos = {form: Counter({"NOUN": 5}) for form in counts}
    pos["Juan"] = Counter({"PROPN": 5})
    with caplog.at_level(logging.WARNING, logger=bo.log.name):
        bo.report_contradictions([counts], pos, "es", tmp_path)
    assert "'estar' over existing 'ser' for 'es'" in caplog.text
    assert "for 'el'" not in caplog.text
    assert "for 'Roma'" not in caplog.text  # case-only, left to the runtime
    assert "for 'Juan'" not in caplog.text  # skipped tag, as in mining


def test_merge_with_existing_warns_on_candidate_collision(tmp_path, caplog):
    """Candidates folding to one key with different lemmas: first wins, with a warning."""
    candidates = {"שָׁלוֹם": "לום", "שלום": "אחר"}  # both fold to שלום
    with caplog.at_level(logging.WARNING, logger=bo.log.name):
        merged, added = bo.merge_with_existing(candidates, "he", tmp_path)
    assert merged == {"שלום": "לום"}
    assert added == 1
    assert "collide" in caplog.text
