import logging
import sys
from collections import Counter

import pytest

import simplemma.sentences as sentences
from training import sentencebuilder, ud_conllu


def _treebank(path, sents: list[str]) -> None:
    """Only the '# text =' lines are read, so a token row would be dead weight."""
    path.write_text("".join(f"# text = {s}\n\n" for s in sents), encoding="utf-8")


def test_gold_sentences_reads_text_lines_only(tmp_path):
    path = tmp_path / "x.conllu"
    path.write_text(
        "# sent_id = 1\n# text = Erste. Zweite\n# text =   \n1\tx\tx\n\n",
        encoding="utf-8",
    )
    assert sentencebuilder.gold_sentences(path) == ["Erste. Zweite"]


def test_sentence_ends_offsets_match_the_joined_text():
    gold = ["Eins.", "Zwei."]
    assert sentencebuilder.sentence_ends(gold, " ") == {5}
    # the last sentence never contributes a boundary
    assert sentencebuilder.sentence_ends(["Nur eins."], " ") == set()


def test_mine_scores_a_starter_by_gold_boundaries(tmp_path):
    # "u. a." suppresses the junction: gold breaks before "Ja", never before "nein"
    path = tmp_path / "de_x-ud-train.conllu"
    _treebank(
        path, ["Er kauft u. a.", "Ja das stimmt.", "Es gilt u. a. nein doch nicht."] * 2
    )
    gain, loss = sentencebuilder.mine("de", [sentencebuilder.gold_sentences(path)])
    assert gain["ja"] == 2
    assert loss["nein"] == 2
    assert "ja" not in loss


def test_select_needs_support_and_a_net_gain():
    gain = Counter({"ja": 5, "knapp": 2, "nein": 3, "einmal": 1})
    loss = Counter({"knapp": 2, "nein": 9})
    assert sentencebuilder.select(gain, loss) == frozenset({"ja"})


def test_boundary_f1_is_one_when_every_boundary_is_found(tmp_path):
    path = tmp_path / "de_x-ud-dev.conllu"
    _treebank(path, ["Das ist ein Satz.", "Und noch einer.", "Dazu ein dritter."])
    assert (
        sentencebuilder.boundary_f1("de", [sentencebuilder.gold_sentences(path)]) == 1.0
    )


def test_starters_replaced_restores_the_runtime_dict():
    before = sentences._STARTERS["de"]
    with sentencebuilder.starters_replaced("de", frozenset({"zzz"})):
        assert sentences._STARTERS["de"] == frozenset({"zzz"})
    assert sentences._STARTERS["de"] is before

    assert "xx" not in sentences._STARTERS
    with sentencebuilder.starters_replaced("xx", frozenset({"a"})):
        assert sentences._STARTERS["xx"] == frozenset({"a"})
    assert "xx" not in sentences._STARTERS


def test_as_literal_round_trips_including_hyphenated_entries():
    starters = frozenset(
        {"aber", "2-gbyte-wechselplatte", "ähnlich", *(f"wort{n}" for n in range(40))}
    )
    literal = sentencebuilder.as_literal("de", starters)
    # eval, not literal_eval: the emitted frozenset(...) call must be valid Python
    parsed = eval("{" + literal.rstrip(",") + "}", {"frozenset": frozenset})  # noqa: S307
    assert parsed == {"de": starters}


def _cli(tmp_path, monkeypatch, lang, *flags):
    licenses = tmp_path / "licenses.tsv"
    licenses.write_text("de_x\tCC BY 4.0\nde_y\tCC BY-NC-SA 4.0\n")
    monkeypatch.setattr(ud_conllu, "UD_LICENSES", licenses)
    monkeypatch.setattr(sentencebuilder, "UD_SPLITS", tmp_path)
    monkeypatch.setattr(sys, "argv", ["sentencebuilder.py", lang, *flags])
    sentencebuilder.main()


def test_main_emits_a_literal_when_the_mined_list_wins(tmp_path, monkeypatch, capsys):
    # "u. a." suppresses the break, only the mined starter "Ja" reopens it
    pairs = ["Er kauft u. a.", "Ja das stimmt."] * 4
    _treebank(tmp_path / "de_x-ud-train.conllu", pairs)
    _treebank(tmp_path / "de_x-ud-dev.conllu", pairs)

    _cli(tmp_path, monkeypatch, "de")

    out = capsys.readouterr().out
    assert '"de": frozenset(' in out
    assert '"ja ' in out
    assert sentences._STARTERS["de"] != frozenset({"ja"})


def test_main_skips_disallowed_train(tmp_path, monkeypatch, capsys, caplog):
    pairs = ["Er kauft u. a.", "Ja das stimmt."] * 4
    _treebank(tmp_path / "de_y-ud-train.conllu", pairs)
    _treebank(tmp_path / "de_x-ud-train.conllu", ["Ein Satz.", "Noch einer."])
    _treebank(tmp_path / "de_x-ud-dev.conllu", pairs)

    with caplog.at_level(logging.WARNING, logger=ud_conllu.log.name):
        _cli(tmp_path, monkeypatch, "de")

    assert "skipping de_y (CC BY-NC-SA 4.0)" in caplog.text
    assert "keep the shipped list" in capsys.readouterr().out


def test_main_errors_without_allowed_train(tmp_path, monkeypatch):
    _treebank(tmp_path / "de_y-ud-train.conllu", ["Ein Satz.", "Noch einer."])
    _treebank(tmp_path / "de_x-ud-dev.conllu", ["Ein Satz.", "Noch einer."])

    with pytest.raises(SystemExit, match="allowed license"):
        _cli(tmp_path, monkeypatch, "de")


def test_main_keeps_the_shipped_list_when_mining_does_not_help(
    tmp_path, monkeypatch, capsys
):
    _treebank(tmp_path / "de_x-ud-dev.conllu", ["Ein Satz.", "Noch einer."])
    _treebank(tmp_path / "de_x-ud-train.conllu", ["Ein Satz.", "Noch einer."])

    _cli(tmp_path, monkeypatch, "de")

    assert "keep the shipped list" in capsys.readouterr().out


def test_main_check_only_scores_the_shipped_list(tmp_path, monkeypatch, capsys):
    _treebank(tmp_path / "de_x-ud-dev.conllu", ["Ein Satz.", "Noch einer."])

    _cli(tmp_path, monkeypatch, "de", "--check")

    out = capsys.readouterr().out
    assert out.startswith("shipped: ")
    assert "mined" not in out


def test_pretokenized_needs_a_majority_of_spaced_dots_or_commas():
    assert sentencebuilder.pretokenized(["Ein Satz .", "Ja , klar .", "Nein."])
    assert not sentencebuilder.pretokenized(["Ein Satz .", "Nein."])
    assert not sentencebuilder.pretokenized(["Qui est-il ?", "Non !"])


def test_main_does_not_score_on_pretokenized_text(tmp_path, monkeypatch, capsys):
    _treebank(tmp_path / "de_x-ud-dev.conllu", ["Ein Satz.", "Noch einer."])
    _treebank(tmp_path / "de_y-ud-dev.conllu", ["Ein Satz .", "Noch einer .", "Ja."])

    _cli(tmp_path, monkeypatch, "de", "--check")

    out = capsys.readouterr().out
    assert "not scoring on de_y-ud-dev.conllu" in out
    assert "over 1 dev treebanks" in out


def test_main_errors_with_only_pretokenized_text(tmp_path, monkeypatch):
    _treebank(tmp_path / "de_y-ud-dev.conllu", ["Ein Satz .", "Noch einer ."])

    with pytest.raises(SystemExit) as excinfo:
        _cli(tmp_path, monkeypatch, "de", "--check")
    assert excinfo.value.code == 2


def test_main_falls_back_to_test_without_dev(tmp_path, monkeypatch, capsys):
    """Without a dev treebank, scoring falls back to test with a warning."""
    _treebank(tmp_path / "de_x-ud-test.conllu", ["Ein Satz.", "Noch einer."])

    _cli(tmp_path, monkeypatch, "de", "--check")

    out = capsys.readouterr().out
    assert out.startswith("WARNING: no dev treebank")
    assert "test treebanks" in out


def test_main_errors_without_a_test_treebank(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as excinfo:
        _cli(tmp_path, monkeypatch, "xx")
    assert excinfo.value.code == 2
