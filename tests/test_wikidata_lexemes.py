import gzip
import json
from pathlib import Path
from typing import Any

import pytest

from simplemma.strategies import DefaultStrategy
from training import wikidata_lexemes as wl
from training.clean_wordlist import write_pairs
from training.dictionary_builder import V2_FILL_LANGS
from training.eval_harness import FixedDictionaryFactory


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


def test_stem_anchored_prune_keeps_self_maps_not_in_shipped():
    """A fill lemma's self-map is kept even when not in shipped, or the pruned
    form would regenerate to a lemma absent from the final dict."""
    shipped: dict[str, str] = {}
    fill_pairs = [("talo", "talo"), ("talo", "talossa")]
    kept, stats = wl.stem_anchored_prune(fill_pairs, shipped, "fi")
    assert kept == [("talo", "talo")]  # the self-map, re-added
    assert stats["pruned"] == 2
    assert stats["self_maps_added"] == 1


def test_stem_anchored_prune_omits_self_maps_already_in_shipped():
    """A self-map already provided by shipped isn't duplicated into kept."""
    shipped = {"talo": "talo"}
    fill_pairs = [("talo", "talossa")]
    kept, stats = wl.stem_anchored_prune(fill_pairs, shipped, "fi")
    assert kept == []  # talossa derivable; talo self-map already in shipped
    assert stats["self_maps_added"] == 0


def test_stem_anchored_prune_self_map_deconflicts_with_kept_form():
    """A self-map (L, L) and a surviving pair with form L can't both ship; the
    conflicting pair is dropped explicitly, not left to append-order last-writer."""
    shipped: dict[str, str] = {}
    # "le" survives pruning as (x -> le) and also earns a self-map (from le -> lesse): a conflict
    fill_pairs = [("x", "le"), ("le", "lesse")]
    kept, stats = wl.stem_anchored_prune(fill_pairs, shipped, "fi")

    forms = [form for _, form in kept]
    assert len(forms) == len(set(forms)), f"duplicate form in {kept!r}"
    assert ("le", "le") in kept  # self-map wins
    assert ("x", "le") not in kept  # conflicting attested pair dropped
    assert stats["dropped_form_lemma_conflict"] == 1


def test_stem_anchored_prune_pruned_form_still_lemmatizes_after_merge():
    """A pruned form must still lemmatize correctly once the kept set is merged."""
    shipped: dict[str, str] = {}
    fill_pairs = [("talo", "talo"), ("talo", "talossa")]
    kept, _ = wl.stem_anchored_prune(fill_pairs, shipped, "fi")

    merged = {form: lemma for lemma, form in kept}
    merged.update(shipped)
    strategy = DefaultStrategy(dictionary_factory=FixedDictionaryFactory(merged))
    assert strategy.get_lemma("talossa", "fi") == "talo"


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


def test_v2_fill_langs_is_the_reviewed_decision():
    """Locks the ship decision: fr/it/tr held (regressions), nb un-gateable
    (no UD treebank). 2026-07-17 wave: nn PASS+shipped (+0.0025/+0.0074
    no_nynorsk-ud-test); id/fa FAILED the gate (id = WD's meN-active lemma
    convention vs shipped's root convention; fa = verb-stem ambiguity noise)
    -- never added; se PASSED but +0.0000pp (already 115k entries/0.95 acc)
    -- dropped by user call despite passing."""
    assert V2_FILL_LANGS <= set(wl.LANGUAGE_QIDS)  # only extractable langs
    assert V2_FILL_LANGS.isdisjoint({"fr", "it", "tr", "id", "fa", "se"})
    assert V2_FILL_LANGS == {
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "fi",
        "la",
        "nb",
        "nl",
        "nn",
        "pl",
        "pt",
        "ru",
        "sk",
        "sv",
        "uk",
    }
