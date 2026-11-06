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


def test_collect_candidates_all_pos_with_top_tags(tmp_path):
    per_tb, tags = _collect(
        tmp_path,
        "es",
        [_conllu([[(1, "el", "el", "PRON"), (2, "corre", "correr", "VERB")]])],
    )
    assert per_tb == [{"el": {"el": 1}, "corre": {"correr": 1}}]
    assert tags == {"el": {"PRON"}, "corre": {"VERB"}}


def test_collect_candidates_inherits_canon(tmp_path):
    """The mined lemma is canonicalized for lang, so overrides ship in the dict key space."""
    per_tb, _ = _collect(tmp_path, "ar", ["1\tب\tبِ\tADP\t_\t_\t0\troot\t_\t_\n\n"])
    assert per_tb == [{"ب": {"ب": 1}}]


def test_collect_candidates_folds_forms_to_key_space(tmp_path):
    """Raw spellings the runtime folds together pool under one NFC key."""
    per_tb, tags = _collect(
        tmp_path,
        "he",
        [_conllu([[(1, "שָׁלוֹם", "שלום", "NOUN"), (2, "שלום", "שלום", "NOUN")]])],
    )
    assert per_tb == [{"שלום": {"שלום": 2}}] and tags == {"שלום": {"NOUN"}}
    per_tb, _ = _collect(
        tmp_path, "fr", [_conllu([[(1, "cafe\u0301", "cafe\u0301", "NOUN")]])]
    )
    assert per_tb == [{"caf\u00e9": {"caf\u00e9": 1}}]


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
        pos = {f: {"PRON"} for f in counts}
    return bo.resolve_overrides([counts], pos, current)


def test_resolve_overrides_keeps_majority_beating_output():
    assert _resolve({"el": {"el": 9, "ella": 1}}) == {"el": "el"}


def test_resolve_overrides_drops_when_output_is_majority():
    assert _resolve({"el": {"el": 9}}, current=lambda form: "el") == {}


def test_resolve_overrides_drops_case_only_change():
    pos = {"Roma": {"NOUN"}}
    assert _resolve({"Roma": {"roma": 9}}, pos, lambda form: form) == {}


def test_resolve_overrides_skips_cased_lemma_of_lowercase_form():
    pos = {"baron": {"NOUN"}}
    assert _resolve({"baron": {"Baron": 9}}, pos) == {}


def test_majority_merges_case_variants():
    assert bo.majority(Counter({"der": 4, "Der": 3, "das": 2})) == ("der", 7 / 9)


def test_resolve_overrides_skips_lowercase_lemma_contradicted_by_lowercase_form():
    counts = {"Premios": {"premios": 9}, "premios": {"premio": 9}}
    pos = {f: {"NOUN"} for f in counts}
    assert _resolve(counts, pos, lambda form: "x") == {"premios": "premio"}


def test_resolve_overrides_keeps_cased_selfmap_despite_lowercase_form():
    counts = {"OS": {"OS": 9}, "os": {"osa": 9}}
    pos = {f: {"NOUN"} for f in counts}
    assert _resolve(counts, pos, lambda form: "x") == {"OS": "OS", "os": "osa"}


def test_resolve_overrides_keeps_lowercase_lemma_with_other_pos_reading():
    counts = {"Stato": {"stato": 9}, "stato": {"essere": 9}}
    pos = {"Stato": {"NOUN"}, "stato": {"AUX"}}
    assert _resolve(counts, pos, lambda form: "x") == {
        "Stato": "stato",
        "stato": "essere",
    }


def test_resolve_overrides_veto_counts_lemma_up_to_case():
    per_tb = [
        {"es": Counter({"ser": 10})},
        {"es": Counter({"ser": 1, "Ser": 2, "estar": 2})},
    ]
    pos = {"es": {"AUX"}}
    assert bo.resolve_overrides(per_tb, pos, lambda form: "estar") == {"es": "ser"}


def test_resolve_overrides_drops_low_count():
    assert _resolve({"rare": {"rare": 2}}) == {}


def test_resolve_overrides_skips_underscore_lemmas():
    assert _resolve({"keerde": {"terug_keren": 9}}) == {}
    assert _resolve({"a_b": {"a_b": 9}}) == {"a_b": "a_b"}


def test_resolve_overrides_skips_letterless_lemmas():
    assert _resolve({"1ste": {"1": 9}}) == {}


def test_resolve_overrides_skips_unshippable_pairs():
    """Kept pairs must survive read_pairs and _layer_entries."""
    counts = {
        "c.q.": {"casu quo": 9},
        "a priori": {"apriori": 9},
        "basic\xadally": {"basically": 9},  # soft hyphen: Cf, read_pairs rejects
        "la": {"la": 9},
    }
    assert _resolve(counts) == {"la": "la"}


def test_resolve_overrides_counts_output_up_to_case():
    counts = {"se": {"se": 3, "el": 2}}
    assert _resolve(counts, current=lambda form: "El") == {}
    agreeing = {"se": Counter({"se": 6})}
    dissenting = {"se": Counter({"se": 1, "el": 3})}
    pos = {"se": {"PRON"}}
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
    pos = {"corre": {"VERB"}}
    assert _resolve(pooled, pos=pos) == {}
    pooled = {"corre": {"correr": 5}}
    assert _resolve(pooled, pos=pos) == {"corre": "correr"}


def test_resolve_overrides_skips_excluded_tags():
    for tag in ("PROPN", "ADP", bo.PARTICIPLE):
        assert _resolve({"dicho": {"decir": 9}}, {"dicho": {tag}}) == {}


def test_resolve_overrides_per_treebank_veto():
    """A treebank with >=3 attestations where the output beats the winner vetoes it."""
    agreeing = {"esse": Counter({"esse": 30})}
    dissenting = {"esse": Counter({"sum": 3})}
    pos = {"esse": {"AUX"}}
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
    train += _conllu([[(1, "corre", "otro", "VERB")]] * 5)  # contradicts a reviewed row
    (splits / "zz_x-ud-train.conllu").write_text(train, encoding="utf-8")
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)

    overrides = tmp_path / "overrides"
    overrides.mkdir()
    (overrides / "zz.tsv").write_text("correr\tcorre\n", encoding="utf-8")
    monkeypatch.setattr(bo, "OVERRIDES_DIR", overrides)
    monkeypatch.setattr(bo, "OUTPUT_DIR", tmp_path / "output")
    langs = []
    monkeypatch.setattr(
        bo, "lemmatize", lambda token, lang: langs.append(lang) or token
    )
    monkeypatch.setattr(sys, "argv", ["build_override", "zz", "--in-place"])

    with caplog.at_level(logging.INFO, logger=bo.log.name):
        bo.main()  # a missing treebank would sys.exit

    assert set(langs) == {"zz"}
    assert "1 new entries over 1 existing" in caplog.text
    assert "'otro' over existing 'correr' for 'corre'" in caplog.text
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
    monkeypatch.setattr(sys, "argv", ["build_override", "--exclude", "zz_y", "zz"])
    bo.main()
    assert (tmp_path / "output" / "zz.tsv").read_text(encoding="utf-8") == (
        "correr\tcorres\n"
    )


def test_main_rejects_unknown_treebank(tmp_path, monkeypatch):
    splits = tmp_path / "splits"
    splits.mkdir()
    (splits / "zz_x-ud-train.conllu").write_text(_conllu([]), encoding="utf-8")
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)
    monkeypatch.setattr(sys, "argv", ["build_override", "zz", "--exclude", "zz_typo"])
    with pytest.raises(SystemExit, match="unknown treebanks"):
        bo.main()


def test_resolve_overrides_ties_are_insertion_order_independent():
    # POS tie AUX/VERB: stricter open-class bar applies whichever came first
    for pos_counts in ({"AUX": 3, "VERB": 3}, {"VERB": 3, "AUX": 3}):
        assert bo.top_tags(Counter(pos_counts)) == {"AUX", "VERB"}
    pooled = {"es": Counter({"ser": 4})}
    assert bo.resolve_overrides([pooled], {"es": {"AUX", "VERB"}}, lambda f: "?") == {}
    # an evenly split treebank loses nothing: no veto
    agreeing = {"esse": Counter({"esse": 30})}
    for split_counts in ({"esse": 3, "sum": 3}, {"sum": 3, "esse": 3}):
        split_tb = {"esse": Counter(split_counts)}
        assert bo.resolve_overrides(
            [agreeing, split_tb], {"esse": {"AUX"}}, lambda f: "sum"
        ) == {"esse": "esse"}


def test_collect_candidates_tags_participles(tmp_path):
    text = "1\tdicho\tdecir\tADJ\t_\tVerbForm=Part\t0\troot\t_\t_\n\n"
    _, tags = _collect(tmp_path, "es", [text])
    assert tags == {"dicho": {bo.PARTICIPLE}}


def test_report_contradictions_warns(caplog):
    existing = {"es": "ser", "el": "el", "Roma": "Roma", "Juan": "Juan", "lo": "le"}
    counts = {
        "es": Counter({"estar": 5}),
        "el": Counter({"el": 5}),
        "Roma": Counter({"roma": 5}),
        "Juan": Counter({"Juanito": 5}),
        "lo": Counter({"él": 3}),
    }
    pos = {form: {"NOUN"} for form in counts}
    pos["Juan"] = {"PROPN"}
    pos["lo"] = {"PRON"}
    with caplog.at_level(logging.WARNING, logger=bo.log.name):
        bo.report_contradictions(counts, pos, existing, "es")
    assert "'estar' over existing 'ser' for 'es'" in caplog.text
    assert "for 'lo'" in caplog.text  # closed class, at its own bar
    assert "for 'el'" not in caplog.text
    assert "for 'Roma'" not in caplog.text  # case-only, left to the runtime
    assert "for 'Juan'" not in caplog.text  # skipped tag, as in mining
