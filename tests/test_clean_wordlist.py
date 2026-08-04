import json
import sys

import pytest

from training import clean_wordlist
from training.clean_wordlist import clean_wordlist as run_clean


def test_nfc_normalization() -> None:
    decomposed = "é"  # e + combining acute
    normalized, _ = clean_wordlist.canonicalize(decomposed)
    assert normalized == "é"  # precomposed é


def test_lookalike_canonicalization() -> None:
    text, counts = clean_wordlist.canonicalize("‘word’")
    assert text == "'word'"
    assert sum(counts.values()) == 2


def test_strip_invisible_chars() -> None:
    text, counts = clean_wordlist.canonicalize("﻿word­​")
    assert text == "word"
    assert sum(counts.values()) == 3


def test_check_field_accepts_plain_latin() -> None:
    assert clean_wordlist.check_field("dogs") is None


def test_check_field_accepts_any_script() -> None:
    """No script policy: letters of any script pass."""
    assert clean_wordlist.check_field("догс") is None  # Cyrillic
    assert clean_wordlist.check_field("犬") is None  # Han


def test_check_field_rejects_control_char() -> None:
    reason = clean_wordlist.check_field("wo\x01rd")
    assert reason is not None
    assert reason.startswith("control_or_unassigned")


def test_check_field_rejects_replacement_char() -> None:
    assert clean_wordlist.check_field("wo�rd") == "replacement_char"


def test_check_field_allows_punctuation_and_digits() -> None:
    assert clean_wordlist.check_field("l'homme-2") is None


def test_check_field_allows_marks() -> None:
    assert clean_wordlist.check_field("é") is None  # é in NFD (base + combining)


def test_check_field_allows_zwnj_and_zwj() -> None:
    """ZWNJ/ZWJ are word-internal joiners in Perso-Arabic/Indic scripts; allowed universally."""
    assert clean_wordlist.check_field("mی‌خواهم") is None  # contains ZWNJ
    assert clean_wordlist.check_field("wo‍rd") is None  # contains ZWJ


def test_check_field_rejects_other_format_chars() -> None:
    """Format chars other than the ZWNJ/ZWJ joiners are still junk."""
    reason = clean_wordlist.check_field("wo⁦rd")  # LEFT-TO-RIGHT ISOLATE
    assert reason is not None
    assert reason.startswith("control_or_unassigned")


def test_clean_wordlist_rejects_malformed_lines() -> None:
    kept, report = run_clean(["dog\tdogs\tcats\n", "\tdogs\n", "dog\t\n"])
    assert kept == []
    assert report.rejected_by_reason["malformed_line"] == 3
    assert report.total == 3
    assert report.kept == 0


def test_clean_wordlist_rejects_column_empty_after_normalize() -> None:
    """A column of only strippable chars normalizes to empty -- must not be emitted."""
    kept, report = run_clean(["­\tword\n"])  # lemma column is just a soft hyphen
    assert kept == []
    assert report.rejected_by_reason["empty_after_normalize"] == 1
    assert report.kept == 0


def test_clean_wordlist_preserves_duplicates() -> None:
    """R2's evidence-count signal depends on line multiplicity -- never dedup."""
    lines = ["run\trunning\n"] * 3
    kept, report = run_clean(lines)
    assert kept == ["run\trunning"] * 3
    assert report.kept == 3


def test_clean_wordlist_normalizes_kept_rows() -> None:
    kept, report = run_clean(["l'ami\tl’ami\n"])  # curly apostrophe in the form
    assert kept == ["l'ami\tl'ami"]  # canonicalized to straight
    assert report.kept == 1


def test_clean_wordlist_end_to_end_mixed_batch() -> None:
    lines = [
        "dog\tdogs\n",
        "dog\tdogs\n",  # duplicate: must survive
        "cat\tca\x01ts\n",  # control char: rejected
        "bad\tline\textra\n",  # malformed: rejected
    ]
    kept, report = run_clean(lines)
    assert kept == ["dog\tdogs", "dog\tdogs"]
    assert report.total == 4
    assert report.kept == 2
    assert report.reject_pct == 50.0


def test_report_to_json_roundtrips() -> None:
    _, report = run_clean(["dog\tdogs\n", "x\tdo\x01gs\n"])
    payload = report.to_json()
    json.dumps(payload)  # must be JSON-serializable
    assert payload["total"] == 2
    assert payload["kept"] == 1
    assert payload["reject_pct"] == 50.0


def test_main_cli_writes_output_and_report(tmp_path, capsys) -> None:
    # reject rate stays under the 5% default threshold: happy path, not drift alarm
    good_lines = "".join(f"dog{i}\tdogs{i}\n" for i in range(19))
    input_path = tmp_path / "en.txt"
    input_path.write_text(good_lines + "cat\tca\x01ts\n", encoding="utf-8")
    output_path = tmp_path / "en.clean.txt"

    sys.argv = ["clean_wordlist.py", str(input_path), str(output_path)]
    clean_wordlist.main()

    kept_text = output_path.read_text(encoding="utf-8")
    assert "dog0\tdogs0" in kept_text
    assert "ca\x01ts" not in kept_text
    report_path = tmp_path / "en.clean.txt.report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kept"] == 19
    assert report["total"] == 20
    captured = capsys.readouterr()
    assert "kept 19/20" in captured.out


def test_main_cli_exits_nonzero_on_drift(tmp_path) -> None:
    """max-reject-pct exceeded -> nonzero exit (data-drift alarm)."""
    input_path = tmp_path / "en.txt"
    # 3 of 4 lines carry a control char: 75% reject, way past the 5% default.
    input_path.write_text("dog\tdogs\n" + "x\tdo\x01gs\n" * 3, encoding="utf-8")
    output_path = tmp_path / "en.clean.txt"

    sys.argv = ["clean_wordlist.py", str(input_path), str(output_path)]
    with pytest.raises(SystemExit) as excinfo:
        clean_wordlist.main()
    assert excinfo.value.code == 1


def test_main_cli_custom_report_path(tmp_path) -> None:
    input_path = tmp_path / "en.txt"
    input_path.write_text("dog\tdogs\n", encoding="utf-8")
    output_path = tmp_path / "out.txt"
    report_path = tmp_path / "custom_report.json"

    sys.argv = [
        "clean_wordlist.py",
        str(input_path),
        str(output_path),
        "--report",
        str(report_path),
    ]
    clean_wordlist.main()
    assert report_path.exists()


def test_read_pairs_basic(tmp_path) -> None:
    path = tmp_path / "override.tsv"
    path.write_text("el\tel\nacest\taceste\n", encoding="utf-8")
    assert clean_wordlist.read_pairs(path) == {"el": "el", "aceste": "acest"}


def test_read_pairs_empty_file(tmp_path) -> None:
    path = tmp_path / "empty.tsv"
    path.write_text("", encoding="utf-8")
    assert clean_wordlist.read_pairs(path) == {}


def test_read_pairs_nfc_normalizes(tmp_path) -> None:
    """Fields are NFC-normalized on read, matching runtime lookups."""
    decomposed = "café"  # e + combining acute
    path = tmp_path / "nfc.tsv"
    path.write_text(f"{decomposed}\t{decomposed}s\n", encoding="utf-8")
    assert clean_wordlist.read_pairs(path) == {"cafés": "café"}


def test_read_pairs_repeated_identical_pair_is_kept_once(tmp_path) -> None:
    path = tmp_path / "dup.tsv"
    path.write_text("el\tel\nel\tel\n", encoding="utf-8")
    assert clean_wordlist.read_pairs(path) == {"el": "el"}


def test_read_pairs_raises_on_malformed_row(tmp_path) -> None:
    path = tmp_path / "bad.tsv"
    path.write_text("el\tel\nnotabhere\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.tsv:2: expected 'lemma<TAB>form'"):
        clean_wordlist.read_pairs(path)


def test_read_pairs_raises_on_empty_field(tmp_path) -> None:
    path = tmp_path / "empty_field.tsv"
    path.write_text("el\tel\nlemma\t\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        clean_wordlist.read_pairs(path)


def test_read_pairs_raises_on_junk_field(tmp_path) -> None:
    path = tmp_path / "junk.tsv"
    path.write_text("el\tel\nbad\tba\x01d\n", encoding="utf-8")
    with pytest.raises(ValueError, match="rejected"):
        clean_wordlist.read_pairs(path)


def test_read_pairs_raises_on_conflicting_form(tmp_path) -> None:
    path = tmp_path / "conflict.tsv"
    path.write_text("acest\taceste\nacela\taceste\n", encoding="utf-8")
    with pytest.raises(ValueError, match="maps to both"):
        clean_wordlist.read_pairs(path)
