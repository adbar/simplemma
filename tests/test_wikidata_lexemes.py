import gzip
import json
from pathlib import Path
from typing import Any

import pytest

from training import wikidata_lexemes as wl
from training.clean_wordlist import write_pairs


def _write_dump(tmp_path: Path, lexemes: list[dict[str, Any]]) -> Path:
    """Mirrors the real dump's byte format: `[`, one compact JSON object per line, `]`."""
    path = tmp_path / "lexemes.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as filehandle:
        filehandle.write("[\n")
        for i, lexeme in enumerate(lexemes):
            suffix = "" if i == len(lexemes) - 1 else ","
            filehandle.write(json.dumps(lexeme, separators=(",", ":")) + suffix + "\n")
        filehandle.write("]\n")
    return path


def _lexeme(lang_qid, lang_code, lemma, forms):
    return {
        "language": lang_qid,
        "lemmas": {lang_code: {"language": lang_code, "value": lemma}},
        "forms": [
            {"representations": {lang_code: {"language": lang_code, "value": f}}}
            for f in forms
        ],
    }


def test_stream_lexemes_parses_real_dump_shape(tmp_path):
    lexemes = [
        _lexeme("Q1860", "en", "windsurf", ["windsurfing"]),
        _lexeme("Q7913", "ro", "casă", ["case"]),
    ]
    path = _write_dump(tmp_path, lexemes)
    assert list(wl.stream_lexemes(path)) == lexemes


def test_stream_lexemes_single_entry(tmp_path):
    """Trailing-comma stripping must also work with exactly one entry (no comma at all)."""
    path = _write_dump(tmp_path, [_lexeme("Q188", "de", "Hund", ["Hunde"])])
    assert list(wl.stream_lexemes(path)) == [_lexeme("Q188", "de", "Hund", ["Hunde"])]


def test_extract_pairs():
    lexeme = _lexeme("Q188", "de", "Hund", ["Hunde", "Hundes"])
    assert list(wl.extract_pairs(lexeme, "de")) == [
        ("Hund", "Hunde"),
        ("Hund", "Hundes"),
    ]


def test_extract_pairs_missing_lemma_in_target_language():
    lexeme = _lexeme("Q188", "de", "Hund", ["Hunde"])
    assert list(wl.extract_pairs(lexeme, "fr")) == []  # no French lemma on this lexeme


def test_extract_pairs_form_missing_representation():
    lexeme = {
        "language": "Q188",
        "lemmas": {"de": {"value": "Hund"}},
        "forms": [{"representations": {"fr": {"value": "chien"}}}],  # no "de" here
    }
    assert list(wl.extract_pairs(lexeme, "de")) == []


def test_stream_lexemes_prefilter_skips_non_matching_lines(tmp_path):
    lexemes = [
        _lexeme("Q1860", "en", "windsurf", ["windsurfing"]),
        _lexeme("Q188", "de", "Hund", ["Hunde"]),
    ]
    path = _write_dump(tmp_path, lexemes)
    result = list(wl.stream_lexemes(path, prefilter=('"language":"Q188"',)))
    assert result == [_lexeme("Q188", "de", "Hund", ["Hunde"])]


def test_stream_lexemes_prefilter_exact_qid_not_a_prefix_match(tmp_path):
    """A QID prefilter must not match a longer QID sharing its digits (Q188 vs Q1880)."""
    lexemes = [_lexeme("Q1880", "xx", "foo", ["bar"])]
    path = _write_dump(tmp_path, lexemes)
    result = list(wl.stream_lexemes(path, prefilter=('"language":"Q188"',)))
    assert result == []


def test_extract_language_filters_by_qid(tmp_path):
    lexemes = [
        _lexeme("Q1860", "en", "windsurf", ["windsurfing"]),
        _lexeme("Q188", "de", "Hund", ["Hunde"]),
        _lexeme("Q188", "de", "Katze", ["Katzen"]),
    ]
    path = _write_dump(tmp_path, lexemes)
    result = list(wl.extract_language(path, "Q188", "de"))
    assert result == [("Hund", "Hunde"), ("Katze", "Katzen")]


def test_drop_ambiguous_keeps_unambiguous_forms():
    pairs = [("run", "running"), ("cat", "cats")]
    kept, stats = wl.drop_ambiguous(pairs)
    assert kept == pairs
    assert stats == {"total_pairs": 2, "ambiguous_forms": 0, "kept_pairs": 2}


def test_drop_ambiguous_drops_conflicting_forms():
    """Two lemmas attested for the same form: unresolvable without an evidence-count signal."""
    pairs = [("bank1", "banks"), ("bank2", "banks"), ("run", "running")]
    kept, stats = wl.drop_ambiguous(pairs)
    assert kept == [("run", "running")]
    assert stats == {"total_pairs": 3, "ambiguous_forms": 1, "kept_pairs": 1}


def test_drop_ambiguous_same_pair_repeated_is_not_ambiguous():
    """The SAME (lemma, form) pair appearing twice is not a conflict."""
    pairs = [("run", "running"), ("run", "running")]
    kept, stats = wl.drop_ambiguous(pairs)
    assert kept == pairs
    assert stats["ambiguous_forms"] == 0


def test_drop_junk_pairs_removes_control_and_mojibake():
    """A control-char/mojibake pair is dropped, so the fill file stays strict-readable."""
    pairs = [("cat", "cats"), ("bad", "ba\x01d"), ("w�rd", "words")]
    kept, stats = wl.drop_junk_pairs(pairs)
    assert kept == [("cat", "cats")]
    assert stats == {"total": 3, "kept": 1}


def test_drop_junk_pairs_keeps_clean_pairs_unchanged():
    pairs = [("café", "cafés"), ("run", "running")]
    kept, stats = wl.drop_junk_pairs(pairs)
    assert kept == pairs
    assert stats == {"total": 2, "kept": 2}


def test_write_pairs(tmp_path):
    output_path = tmp_path / "out.tsv"
    count = write_pairs([("Hund", "Hunde"), ("Katze", "Katzen")], output_path)
    assert count == 2
    assert output_path.read_text(encoding="utf-8") == "Hund\tHunde\nKatze\tKatzen\n"


def test_main_end_to_end(tmp_path, monkeypatch):
    lexemes = [
        _lexeme("Q188", "de", "Hund", ["Hunde", "Hund"]),  # self-identity form
        _lexeme("Q188", "de", "Katze", ["Katzen"]),
        _lexeme("Q1860", "en", "cat", ["cats"]),  # different language: excluded
    ]
    dump_path = _write_dump(tmp_path, lexemes)
    output_path = tmp_path / "de_wikidata.tsv"

    monkeypatch.setattr(
        "sys.argv",
        ["wikidata_lexemes.py", "de", str(dump_path), str(output_path)],
    )
    wl.main()

    result = output_path.read_text(encoding="utf-8")
    assert "Hund\tHunde" in result
    assert "Katze\tKatzen" in result
    assert "cat" not in result


def test_main_exits_nonzero_on_zero_pairs(tmp_path, monkeypatch):
    """A dump with no matching lexemes must fail loud, not write an empty fill file."""
    dump_path = _write_dump(tmp_path, [_lexeme("Q1860", "en", "cat", ["cats"])])
    output_path = tmp_path / "de_wikidata.tsv"
    monkeypatch.setattr(
        "sys.argv",
        ["wikidata_lexemes.py", "de", str(dump_path), str(output_path)],  # no Q188
    )
    with pytest.raises(SystemExit) as excinfo:
        wl.main()
    assert excinfo.value.code == 1
    assert not output_path.exists()


def test_language_qids_are_distinct():
    assert len(wl.LANGUAGE_QIDS) == len(set(wl.LANGUAGE_QIDS.values()))
