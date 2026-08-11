"""Integrity guards for the hand-typed Unicode literals in the per-language
tables. These literals are invisible in diffs and one editor-normalization
away from silent corruption -- this arc shipped two of them wrong before an
ad-hoc check caught it (Hebrew table, then the Arabic table missing U+0658).
Each test regenerates the expected codepoint set from `unicodedata` so the
literal can never silently drift."""

import re
import unicodedata

from simplemma.tokenizer import _MARKS
from simplemma.utils import (
    _ARABIC_MARKS,
    _CANON_TABLES,
    _GRAVE_TO_ACUTE,
    _HEBREW_POINTS,
)
from training.build_lang_config import (
    _HBS_CYR_TO_LAT,
    _HBS_PITCH_MARKS,
    BUILD_NORMALIZATION,
    _mark_fold_table,
)


def test_hebrew_points_table_is_exactly_the_block_combining_marks() -> None:
    expected = {
        cp for cp in range(0x0591, 0x05C8) if unicodedata.category(chr(cp)) == "Mn"
    }
    assert set(_HEBREW_POINTS) == expected
    assert all(v is None for v in _HEBREW_POINTS.values())  # a deletion table


def test_arabic_marks_table_is_tashkeel_plus_dagger_alef_and_tatweel() -> None:
    tashkeel = {
        cp for cp in range(0x064B, 0x0660) if unicodedata.category(chr(cp)) == "Mn"
    }
    # + U+0670 superscript alef (Mn) + U+0640 tatweel (Lm, an elongation stroke)
    expected = tashkeel | {0x0670, 0x0640}
    assert set(_ARABIC_MARKS) == expected
    assert all(v is None for v in _ARABIC_MARKS.values())  # a deletion table


def test_grave_to_acute_table_matches_greek_varia_oxia_pairs() -> None:
    # NFC on the OXIA value: build and runtime both NFC-normalize around the
    # fold, so a bare-vowel acute canonicalizes to tonos (U+03AC) not oxia
    # (U+1F71) -- the shipped literal's NFC form is the correct one.
    expected = {}
    for cp in range(0x0370, 0x2000):
        try:
            name = unicodedata.name(chr(cp))
        except ValueError:
            continue
        if "VARIA" in name and name.startswith(
            ("GREEK SMALL LETTER", "GREEK CAPITAL LETTER")
        ):
            oxia = unicodedata.normalize(
                "NFC", unicodedata.lookup(name.replace("VARIA", "OXIA"))
            )
            assert len(oxia) == 1
            expected[cp] = ord(oxia)
    assert _GRAVE_TO_ACUTE == expected


def test_tokenizer_marks_hebrew_and_arabic_ranges_are_exact() -> None:
    """The Hebrew/Arabic portions this arc added to _MARKS must match their
    block's combining marks exactly (a shifted hex boundary is the fat-finger
    risk). The Hebrew set must also equal the canon table's -- both are the
    same block's Mn. (Devanagari includes a few non-Mn signs by design, e.g.
    avagraha U+093D, so the whole class is NOT purely category M.)"""
    cls = re.compile(f"[{_MARKS}]")
    hebrew = {cp for cp in range(0x0591, 0x05C8) if cls.match(chr(cp))}
    assert hebrew == set(_HEBREW_POINTS)
    arabic = {cp for cp in range(0x064B, 0x0671) if cls.match(chr(cp))}
    tashkeel = {
        cp for cp in range(0x064B, 0x0660) if unicodedata.category(chr(cp)) == "Mn"
    }
    assert arabic == tashkeel | {0x0670}  # tashkeel + dagger alef (no tatweel here)
    # fat-finger sanity: nothing below the combining-diacritics block
    assert not any(cls.match(chr(cp)) for cp in range(0x00, 0x0300))


def test_tokenizer_marks_malayalam_range_is_exact() -> None:
    """The Malayalam portion of _MARKS must be exactly the block's Mn/Mc
    codepoints, excluding the two Lo letters (avagraha U+0D3D, dot reph
    U+0D4E) that sit inside the same span but are base letters, not marks."""
    cls = re.compile(f"[{_MARKS}]")
    malayalam = {cp for cp in range(0x0D00, 0x0D80) if cls.match(chr(cp))}
    expected = {
        cp
        for cp in range(0x0D00, 0x0D80)
        if unicodedata.category(chr(cp)) in ("Mn", "Mc")
    }
    assert malayalam == expected
    assert 0x0D3D not in malayalam  # avagraha, a letter
    assert 0x0D4E not in malayalam  # dot reph, a letter


def test_key_alias_table_fa_combines_ar_tashkeel_and_letter_variants() -> None:
    """fa's alias table is _ARABIC_MARKS (the same tashkeel/tatweel deletion
    table ar's canon fold uses -- a deliberate reuse, not a coincidence)
    PLUS the Arabic-script ي/ك -> Persian ی/ک letter substitution, merged
    into one table so a key needing both fixes gets a single fully-
    normalized alias. This guards against the two drifting apart if
    _ARABIC_MARKS is edited later."""
    fa_table = BUILD_NORMALIZATION["fa"].key_alias
    assert fa_table is not None
    assert dict(_ARABIC_MARKS).items() <= fa_table.items()
    letters = {k: v for k, v in fa_table.items() if k not in _ARABIC_MARKS}
    assert {chr(k): chr(v) for k, v in letters.items() if isinstance(v, int)} == {
        "ي": "ی",  # Arabic ya -> Persian ye
        "ك": "ک",  # Arabic kaf -> Persian keheh
    }


def test_value_normalize_table_fa_is_the_same_object_as_the_key_alias() -> None:
    """fa's value rewrite and key alias must be the exact same table object
    (both mark-deletion AND letter-fold) -- not just equal, `is` -- so the
    two mechanisms can never drift apart on what "fa spelling cleanup"
    means (as two hand-synced tables once silently did)."""
    assert BUILD_NORMALIZATION["fa"].value_fold is BUILD_NORMALIZATION["fa"].key_alias


def test_key_alias_table_ar_folds_hamza_seats_and_maqsura() -> None:
    mapping = BUILD_NORMALIZATION["ar"].key_alias
    assert mapping is not None
    assert all(v is not None for v in mapping.values())  # substitution, not deletion
    assert {chr(k): chr(v) for k, v in mapping.items() if isinstance(v, int)} == {
        "أ": "ا",  # hamza above
        "إ": "ا",  # hamza below
        "آ": "ا",  # madda
        "ٱ": "ا",  # wasla
        "ى": "ي",  # alef maqsura -> ya
    }


def test_canon_tables_registered_langs() -> None:
    assert set(_CANON_TABLES) == {"grc", "he", "ar"}


def test_mark_fold_table_generic_deletion_and_precomposed_carriers() -> None:
    """The generic generator behind every per-language mark fold: deletes the
    combining marks themselves, folds every precomposed carrier in range to
    plain, and `keep` protects a letter from folding even though its
    decomposition contains a target mark (the ć-trap, in miniature)."""
    acute = frozenset({0x0301})
    table = _mark_fold_table(acute, keep="éÉ")
    assert table[0x0301] is None  # the combining mark itself: deleted
    assert "é".translate(table) == "é"  # kept: absent from the table
    assert "á".translate(table) == "a"  # folded: precomposed carrier
    assert "a".translate(table) == "a"  # unrelated letter: untouched
    assert "ά".translate(table) == "ά"  # Greek carrier: outside default scripts
    greek = _mark_fold_table(acute, scripts=("GREEK ",))
    assert "ά".translate(greek) == "α"  # folded once its script is named


def test_hbs_pitch_fold_protects_orthographic_letters() -> None:
    """The fold strips pitch/length marks but must never touch the real BCS
    alphabet: ć/Ć (orthographic acute -- a naive NFD strip corrupts them to
    c/C), č/š/ž (caron is not in the mark set), đ (atomic). And it must fold
    both combining marks and their PRECOMPOSED carriers (a combining-only
    probe missed 79k marked keys once)."""
    table = BUILD_NORMALIZATION["hbs"].key_alias
    assert table is not None
    assert BUILD_NORMALIZATION["hbs"].value_fold is table  # shared, fa-style
    kept = "ćĆčČšŠžŽđĐ"
    assert kept.translate(table) == kept
    assert "Hr̀vātskā".translate(table) == "Hrvatska"  # combining marks
    assert "Afganìstān".translate(table) == "Afganistan"  # precomposed ì/ā
    assert "ки̏лограм".translate(table) == "килограм"  # Cyrillic + double grave
    # expected mark set: grave, acute, macron, double grave, inverted breve,
    # circumflex; NOT breve (U+0306) and NOT caron (U+030C)
    assert _HBS_PITCH_MARKS == {0x0300, 0x0301, 0x0304, 0x030F, 0x0311, 0x0302}
    # every mapping folds a char whose decomposition carries a target mark
    for cp, folded in table.items():
        if folded is None:
            assert cp in _HBS_PITCH_MARKS
            continue
        decomposed = unicodedata.normalize("NFD", chr(cp))
        assert any(ord(c) in _HBS_PITCH_MARKS for c in decomposed), hex(cp)
        assert isinstance(folded, str)
        # idempotent: folding a folded char changes nothing further
        assert folded.translate(table) == folded, (hex(cp), folded)


def test_hbs_cyr_to_lat_is_the_full_serbian_alphabet() -> None:
    """Exactly the 30 Serbian Cyrillic letters, both cases; digraph targets
    title-cased (Љ -> Lj). Deterministic direction only -- there is no
    Latin -> Cyrillic table anywhere, that direction is ambiguous."""
    assert len(_HBS_CYR_TO_LAT) == 60
    assert "љубав".translate(_HBS_CYR_TO_LAT) == "ljubav"
    assert "Џорџија".translate(_HBS_CYR_TO_LAT) == "Džordžija"
    assert "Њујорк".translate(_HBS_CYR_TO_LAT) == "Njujork"
    assert "ђак".translate(_HBS_CYR_TO_LAT) == "đak"
    # round-trip sanity on plain letters
    assert "Милорад".translate(_HBS_CYR_TO_LAT) == "Milorad"
    # non-Serbian Cyrillic (Russian ы/э/ё) must NOT be in the table
    assert not {ord("ы"), ord("э"), ord("ё")} & set(_HBS_CYR_TO_LAT)
