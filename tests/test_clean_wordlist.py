import pytest

from training import clean_wordlist


def test_nfc_normalization() -> None:
    decomposed = "é"  # e + combining acute
    assert clean_wordlist.canonicalize(decomposed) == "é"  # precomposed é


def test_lookalike_canonicalization() -> None:
    assert clean_wordlist.canonicalize("‘word’") == "'word'"


def test_strip_invisible_chars() -> None:
    assert clean_wordlist.canonicalize("﻿word­​") == "word"


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
