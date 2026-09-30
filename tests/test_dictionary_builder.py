import logging
from pathlib import Path

import pytest

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory
from simplemma.strategies.dictionaries import dictionary_factory
from training.frontcode_encode import _decode as _fc_decode, _encode as _fc_encode
from simplemma.strategies.dictionaries.dictionary_factory import MappingStrToByteString
from training import build_lang_config, dictionary_builder, wordlist_ingest

TEST_DIR = Path(__file__).parent


def _read(tmp_path, lang: str, text: str) -> dict[str, str]:
    """Write a TSV fixture and return the parsed dictionary."""
    fixture = tmp_path / f"{lang}.txt"
    fixture.write_text(text, encoding="utf-8")
    return wordlist_ingest.read_wordlist(fixture, lang)


def _make_shipped(tmp_path, monkeypatch, text: str) -> None:
    """Build a zz.plzma and install it as the shipped dict (DATA_FOLDER -> tmp_path)."""
    (tmp_path / "zz.txt").write_text(text, encoding="utf-8")
    wordlist_ingest.ingest("zz", tmp_path, filepath=str(tmp_path / "zz.plzma"))
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset({"zz"}))


def _layers(tmp_path, monkeypatch, *, overrides: str | None = None):
    """Point OVERRIDES_DIR at a tmp dir with the given zz.tsv, or a missing dir if None."""
    directory = tmp_path / "overrides"
    if overrides is not None:
        directory.mkdir(exist_ok=True)
        (directory / "zz.tsv").write_text(overrides, encoding="utf-8")
    monkeypatch.setattr(dictionary_builder, "OVERRIDES_DIR", directory)


def test_logic(tmp_path, monkeypatch) -> None:
    mydict = wordlist_ingest.read_wordlist(TEST_DIR / "data/zz.txt", "zz")
    assert len(mydict) == 6

    listpath = TEST_DIR / "data"
    temp_outputfile = str(tmp_path / "zz.plzma")
    wordlist_ingest.ingest("zz", listpath, temp_outputfile)
    roundtripped = _fc_decode(Path(temp_outputfile).read_bytes())
    assert isinstance(roundtripped, dict)
    assert len(roundtripped) == 6
    assert all(isinstance(k, bytes) for k in roundtripped)

    # dictionary_builder reads DATA_FOLDER from the factory module at call time
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    wordlist_ingest.ingest("zz", listpath, in_place=True)
    assert (tmp_path / "zz.plzma").exists()


def test_read_dict_filtering(tmp_path) -> None:
    """Punctuation and length-difference drops, plus conflict resolution."""
    result = _read(
        tmp_path,
        "en",
        "dog\tdogs\n"
        "foo,bar\tbaz\n"  # comma in lemma -> dropped
        "new york\tnyc\n"  # space in lemma -> dropped
        "good\t-bad\n"  # leading-hyphen form -> dropped
        "a\tverylongword\n"
        "verylonglemma\tx\n"
        "run\trunning\n"
        "xunning\trunning\n",  # tied counts: closer lemma wins
    )
    assert result == {
        "dog": "dog",
        "dogs": "dog",
        "run": "run",
        "running": "xunning",
        "xunning": "xunning",  # losing a conflict doesn't cost the identity
    }


def test_read_dict_applies_character_hygiene(tmp_path) -> None:
    """Curly apostrophes fold, invisible chars strip, control chars still drop."""
    result = _read(
        tmp_path,
        "en",
        "l'ami\tl’ami\n"  # curly apostrophe in the form -> straight
        "word\two\u00adrds\n"  # soft hyphen stripped
        "bad\tba\x01d\n",  # control char -> line dropped
    )
    assert result == {"l'ami": "l'ami", "words": "word", "word": "word"}


def test_read_dict_order_independent(tmp_path) -> None:
    lines = ["de\tde\n", "een\tde\n", "dog\tdogs\n"]
    forward = _read(tmp_path, "de", "".join(lines))
    reverse = _read(tmp_path, "de", "".join(reversed(lines)))
    assert forward == reverse


def test_read_dict_attested_identity_beats_lone_challenger(tmp_path) -> None:
    result = _read(tmp_path, "de", "de\tde\neen\tde\n")
    assert result["de"] == "de"


def test_read_dict_attestation_count_beats_distance(tmp_path) -> None:
    result = _read(
        tmp_path,
        "en",
        "run\trunning\n" * 2 + "runninx\trunning\n",
    )
    assert result["running"] == "run"


def test_ensure_value_selfmaps() -> None:
    """Every value gains a selfmap unless already a key, unreachable, or letterless."""
    from training.dictionary_builder import _ensure_value_selfmaps

    result = _ensure_value_selfmaps(
        {
            "dogs": "dog",
            "cats": "cat",
            "cat": "kitten",  # 'cat' already a key -> its mapping stands
            "als": "Als Sund",  # space: unreachable, no self-map
            "x1": "123",  # letterless value, no self-map
        }
    )
    assert result["dog"] == "dog"
    assert result["kitten"] == "kitten"
    assert result["cat"] == "kitten"
    assert "Als Sund" not in result
    assert "123" not in result


def test_read_dict_paradigm_prior_breaks_ties(tmp_path) -> None:
    """In PARADIGM_PRIOR_LANGS a tie goes to the larger paradigm, not the closer lemma."""
    lines = "εἰμί\tἦν\n" * 2 + "ἠμί\tἦν\n" * 2 + "εἰμί\tἐστί\nεἰμί\tἦσαν\n"
    assert _read(tmp_path, "grc", lines)["ἦν"] == "εἰμί"
    # same shape in an unregistered language keeps the distance tie-break
    lines = "abcd\tab\n" * 2 + "abx\tab\n" * 2 + "abcd\tabcde\nabcd\tabcdf\n"
    assert _read(tmp_path, "en", lines)["ab"] == "abx"


def test_read_dict_lemma_headword_never_reduces(tmp_path) -> None:
    """A lemma headword maps to itself even when also listed as a form."""
    result = _read(tmp_path, "en", "lansa\tlansat\nlansat\tlansare\n")
    assert result["lansat"] == "lansat"
    assert result["lansare"] == "lansat"


def test_read_dict_soft_identity_for_grc(tmp_path) -> None:
    """grc keeps the attested mapping of a word that is also a headword."""
    result = _read(tmp_path, "grc", "ἀκούω\tἀκούσας\n" * 5 + "ἀκούσας\tἀκούσας\n")
    assert result["ἀκούσας"] == "ἀκούω"


def test_read_dict_self_only_lemma_is_soft(tmp_path) -> None:
    """A self-only lemma yields to its attested mapping, a paradigm head does not."""
    al_headword = "كتاب\tالكتاب\n" * 5 + "الكتاب\tالكتاب\n"  # self-only lemma
    non_al_headword = "قلم\tبيت\n" * 5 + "بيت\tبيوت\n"  # بيت heads a paradigm
    result = _read(tmp_path, "ar", al_headword + non_al_headword)
    assert result["الكتاب"] == "كتاب"
    assert result["بيت"] == "بيت"


def test_read_dict_rejects_maqaf_edged_fields(tmp_path) -> None:
    """Hebrew maqaf (U+05BE) acts as a hyphen, so maqaf-edged fields drop."""
    result = _read(
        tmp_path,
        "he",
        "ב־\tבו\n"  # maqaf-edged lemma -> line dropped
        "כלב\tכלבים\n",
    )
    assert "בו" not in result
    assert result["כלבים"] == "כלב"


def test_read_dict_canonicalizes_grc_accents(tmp_path) -> None:
    """grc grave accents fold to acute, matching canonicalize_token at runtime."""
    result = _read(tmp_path, "grc", "ἐγώ\tἐγὼ\n")
    assert result == {"ἐγώ": "ἐγώ"}  # grave form folded to the acute key


def test_add_key_aliases_ar_hamza() -> None:
    """ar: a hamza or alef-maqsura key gains a folded alias, the value is untouched."""
    table = build_lang_config.BUILD_NORMALIZATION["ar"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases({"أحمد": "أحمد", "بيت": "بيت"}, table)
    assert result["احمد"] == "أحمد"
    assert result["أحمد"] == "أحمد"
    assert "بيت" in result and "بىت" not in result  # no hamza or maqsura, no alias


def test_add_key_aliases_never_overwrites_an_existing_exact_key() -> None:
    table = build_lang_config.BUILD_NORMALIZATION["ar"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"أمن": "أمن", "امن": "امن_different_word"}, table
    )
    assert result["امن"] == "امن_different_word"


def test_add_key_aliases_ru_yo() -> None:
    """ru: a ё key gains an е twin, but a real е entry wins (все and всё differ)."""
    table = build_lang_config.BUILD_NORMALIZATION["ru"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"ребёнка": "ребёнок", "всё": "всё", "все": "весь"}, table
    )
    assert result["ребенка"] == "ребёнок"
    assert result["все"] == "весь"


def test_add_key_aliases_hbs_pitch_marks() -> None:
    """hbs: a pitch-marked key gains a plain twin, and both survive by default."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"Hr̀vātskā": "Hrvatska", "vȉde": "vidjeti", "vide": "videti"}, table
    )
    assert result["Hrvatska"] == "Hrvatska"
    assert result["vide"] == "videti"
    assert "Hr̀vātskā" in result


def test_add_key_aliases_drop_original() -> None:
    """drop_original=True replaces the marked key, a real plain entry still wins."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"Hr̀vātskā": "Hrvatska", "vȉde": "vidjeti", "vide": "videti"},
        table,
        drop_original=True,
    )
    assert result == {"Hrvatska": "Hrvatska", "vide": "videti"}
    assert "Hr̀vātskā" not in result
    assert "vȉde" not in result


def test_hbs_pitch_fold_keeps_montenegrin_letters() -> None:
    """ś and ź are real Montenegrin letters and must survive the pitch fold."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].key_alias
    assert table is not None
    for ch in "śŚźŹ":
        assert ch.translate(table) == ch
    result = dictionary_builder._apply_build_normalization(
        {"dośetka": "dośetka", "źenica": "źenica"}, "hbs"
    )
    assert result == {"dośetka": "dośetka", "źenica": "źenica"}


def test_apply_build_normalization_hbs_drops_marked_originals() -> None:
    """drop_folded_keys is wired through _apply_build_normalization."""
    result = dictionary_builder._apply_build_normalization(
        {"Hr̀vātskā": "Hrvatska"}, "hbs"
    )
    assert result == {"Hrvatska": "Hrvatska"}


def test_apply_build_normalization_ru_keeps_original() -> None:
    """ru text really uses ё, so the original key is kept."""
    result = dictionary_builder._apply_build_normalization({"ребёнка": "ребёнок"}, "ru")
    assert result == {"ребёнка": "ребёнок", "ребенка": "ребёнок"}


def test_fix_value_scripts_hbs() -> None:
    """Latin keys get Latin values, other keys and non-Serbian values stay as is."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].value_script_fix
    assert table is not None
    result = dictionary_builder._fix_value_scripts(
        {
            "Milorad": "Милорад",
            "jun": "јун",
            "Милорад": "Милорад",
            "atoмска": "атомски",
            "boršč": "боршчёвый",  # ё is not Serbian: left unchanged
        },
        table,
    )
    assert result["Milorad"] == "Milorad"
    assert result["jun"] == "jun"
    assert result["Милорад"] == "Милорад"
    assert result["atoмска"] == "атомски"
    assert result["boršč"] == "боршчёвый"


def test_add_key_aliases_never_plants_an_empty_key() -> None:
    """A mark-only key folds to an empty string under fa and must not alias."""
    table = build_lang_config.BUILD_NORMALIZATION["fa"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases({"ـ": "ـ"}, table)
    assert result == {"ـ": "ـ"}


def test_apply_build_normalization_noop_for_unregistered_langs() -> None:
    d = {"أحمد": "أحمد"}
    assert dictionary_builder._apply_build_normalization(d, "zz") == d


def test_drop_junk_keys_uk_paradigm_codes() -> None:
    """uk: paradigm codes and footnotes drop, no Ukrainian word starts with a digit."""
    result = dictionary_builder._drop_junk_keys(
        {"10a": "вибороти", "¹Rare.": "літ", "мати": "мати"}, "uk"
    )
    assert result == {"мати": "мати"}


def test_drop_junk_keys_uk_latin_homoglyphs() -> None:
    """uk: a key mixing Latin and Cyrillic letters is homoglyph noise."""
    result = dictionary_builder._drop_junk_keys(
        {
            "cказився": "сказитися",
            "ремонтно-механічнe": "ремонтно-механічний",
            "мати": "мати",
        },
        "uk",
    )
    assert result == {"мати": "мати"}


def test_drop_junk_keys_grc_gloss_values() -> None:
    """grc drops English gloss values, their selfmaps, and Beta-code keys."""
    result = dictionary_builder._drop_junk_keys(
        {"κάλαμος": "plants", "plants": "plants", "hubrisin": "ὑβρίς", "ἦν": "εἰμί"},
        "grc",
    )
    assert result == {"ἦν": "εἰμί"}


def test_drop_junk_keys_wholly_foreign_identity() -> None:
    """Wholly foreign identity rows drop, except bg Latin abbreviations and he Phoenician."""
    assert dictionary_builder._drop_junk_keys({"vony": "vony"}, "uk") == {}
    assert (
        dictionary_builder._drop_junk_keys(
            {"overweight": "overweight", "אללה": "אללה"}, "ar"
        )
        == {}
    )
    assert dictionary_builder._drop_junk_keys({"sweets": "sweets"}, "hi") == {}
    assert dictionary_builder._drop_junk_keys(
        {"and": "بودن", "jewels": "jewels", "بودن": "بودن"}, "fa"
    ) == {"بودن": "بودن"}
    assert dictionary_builder._drop_junk_keys({"DM": "dm"}, "bg") == {"DM": "dm"}
    phoenician = {"𐤉𐤄𐤅𐤄": "𐤉𐤄𐤅𐤄"}
    assert dictionary_builder._drop_junk_keys(phoenician, "he") == phoenician


def test_selfmaps_are_planted_before_junk_keys_are_dropped() -> None:
    """A selfmap planted for a junk value is filtered too."""
    # the c is Latin
    planted = dictionary_builder._ensure_value_selfmaps({"мати": "cказився"})
    assert planted["cказився"] == "cказився"
    assert dictionary_builder._drop_junk_keys(planted, "uk") == {"мати": "cказився"}
    planted = dictionary_builder._ensure_value_selfmaps({"κάλαμος": "plants"})
    assert planted["plants"] == "plants"
    assert dictionary_builder._drop_junk_keys(planted, "grc") == {}


def test_drop_junk_keys_noop_for_other_langs() -> None:
    """Digit-leading keys are real words in many languages."""
    d = {"10a": "10a", "1000ú": "1000ú"}
    assert dictionary_builder._drop_junk_keys(d, "ga") == d


def test_drop_junk_keys_tl_baybayin() -> None:
    """tl: Baybayin keys drop even when the value is also Baybayin."""
    result = dictionary_builder._drop_junk_keys(
        {"ᜀᜀᜃᜓᜀ": "akuin", "ᜇ": "ᜇ", "akuin": "akuin"}, "tl"
    )
    assert result == {"akuin": "akuin"}


def test_drop_junk_keys_he_latin_transliterations() -> None:
    """he: Latin keys with Hebrew values drop, other keys stay."""
    result = dictionary_builder._drop_junk_keys(
        {"Slitherin": "סלית׳רין", "בית": "בית", "3": "3"}, "he"
    )
    assert result == {"בית": "בית", "3": "3"}


def _foreign_script_key(key: str, value: str, allowed: frozenset[str]) -> bool:
    """Adapt strings to the precomputed script sets the predicate takes."""
    return build_lang_config._foreign_script_key(
        dictionary_builder._script_classes(key),
        dictionary_builder._script_classes(value),
        allowed,
    )


_FOREIGN_SCRIPT_KEY_CASES = [
    pytest.param("uð.ðu.ki.ruː", "اذكروا", frozenset({"ARABIC"}), True, id="ar-ipa"),
    pytest.param(
        "hubrisin",
        "ὑβρίς",
        frozenset({"GREEK", "CYPRIOT", "LINEAR"}),
        True,
        id="grc-betacode",
    ),
    # Cypriot syllabary is a real alternate script
    pytest.param(
        "𐠞𐠪𐠐𐠄𐠩",
        "βασιλεύς",
        frozenset({"GREEK", "CYPRIOT", "LINEAR"}),
        False,
        id="grc-cypriot-kept",
    ),
    # ms: only Rumi keys with Jawi values are noise
    pytest.param("جون", "Jun", frozenset({"ARABIC"}), False, id="ms-jawi-to-rumi"),
    pytest.param("pintu", "ڤينتو", frozenset({"ARABIC"}), True, id="ms-rumi-to-jawi"),
    pytest.param(
        "atoмска",
        "атомски",
        frozenset({"CYRILLIC"}),
        False,
        id="mixed-script",
    ),
    pytest.param("123", "число", frozenset({"CYRILLIC"}), False, id="non-alphabetic"),
]


@pytest.mark.parametrize("key, value, allowed, expected", _FOREIGN_SCRIPT_KEY_CASES)
def test_is_foreign_script_key(
    key: str, value: str, allowed: frozenset[str], expected: bool
) -> None:
    assert _foreign_script_key(key, value, allowed) is expected


def test_drop_junk_keys_ar_ipa_rows() -> None:
    result = dictionary_builder._drop_junk_keys(
        {"uð.ðu.ki.ruː": "اذكروا", "كتاب": "كتاب"}, "ar"
    )
    assert result == {"كتاب": "كتاب"}


def test_drop_junk_keys_hi_urdu_script_leak() -> None:
    """hi: Perso-Arabic entries leaked from shared Hindi/Urdu extraction drop."""
    result = dictionary_builder._drop_junk_keys({"سفید": "सफ़ेद", "सफ़ेद": "सफ़ेद"}, "hi")
    assert result == {"सफ़ेद": "सफ़ेद"}


def test_drop_junk_keys_ms_keeps_jawi_to_rumi_direction() -> None:
    result = dictionary_builder._drop_junk_keys({"جون": "Jun", "pintu": "ڤينتو"}, "ms")
    assert result == {"جون": "Jun"}


def test_build_dictionary_ships_ar_hamza_alias(tmp_path, monkeypatch) -> None:
    """A built ar .plzma ships both the hamza key and its folded alias."""
    # ar ships, so unlist it to skip layering the real dict
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset())
    (tmp_path / "ar.txt").write_text("أحمد\tأحمد\n", encoding="utf-8")
    outfile = str(tmp_path / "ar.plzma")
    wordlist_ingest.ingest("ar", tmp_path, outfile)
    built = _fc_decode(Path(outfile).read_bytes())
    assert built["أحمد".encode()] == "أحمد".encode()
    assert built["احمد".encode()] == "أحمد".encode()


def test_read_dict_keeps_long_and_single_char_entries(tmp_path) -> None:
    """Long forms and 1-char lemmas are kept."""
    result = _read(
        tmp_path,
        "fi",
        "pitkä\tpitkänmatkanjuoksija\no\to\n",
    )
    assert result["pitkänmatkanjuoksija"] == "pitkä"
    assert result["o"] == "o"


def test_read_dict_normalizes_to_nfc(tmp_path) -> None:
    """Keys and values are NFC, since runtime lookups NFC-normalize."""
    decomposed = "café"  # NFD: e + combining acute
    result = _read(tmp_path, "en", f"{decomposed}\t{decomposed}s\n")
    assert result == {"café": "café", "cafés": "café"}


def test_read_dict_rejects_control_and_mojibake_keys(tmp_path) -> None:
    """Control and mojibake lines drop even without clean_wordlist."""
    result = _read(tmp_path, "en", "dog\tdogs\nbad\tba\x01d\nx\tw�rd\n")
    assert result == {"dog": "dog", "dogs": "dog"}


def _layer(tmp_path, text: str) -> dict[str, str]:
    path = tmp_path / "zz.tsv"
    path.write_text(text, encoding="utf-8")
    return dictionary_builder._layer_entries(path, "zz")


def test_layer_entries_drops_spaced_forms(tmp_path) -> None:
    """Spaced layer forms are unreachable, the tokenizer never yields them."""
    assert _layer(tmp_path, "top hat\ttop hats\ncat\tcats\n") == {"cats": "cat"}


def test_layer_entries_rejects_junk_entries(tmp_path) -> None:
    """Mojibake or control chars in a layer file fail the build."""
    with pytest.raises(ValueError, match="rejected"):
        _layer(tmp_path, "good\tgoods\nbad\tba\x01d\n")


def test_layer_entries_rejects_empty_fields(tmp_path) -> None:
    """An empty lemma or form in a layer file fails the build."""
    with pytest.raises(ValueError, match="empty"):
        _layer(tmp_path, "good\tgoods\nlemma\t\n")


def test_layer_entries_canonicalizes_a_grc_override(tmp_path) -> None:
    """A grave-accented override ships under its acute key, like the base list."""
    path = tmp_path / "grc.tsv"
    path.write_text("ἐγώ\tἐγὼ\n", encoding="utf-8")
    entries = dictionary_builder._layer_entries(path, "grc")
    assert entries == {"ἐγώ": "ἐγώ"}


def test_layer_entries_rejects_a_canon_collision(tmp_path) -> None:
    """Override lines folding to one form with different lemmas fail the build."""
    path = tmp_path / "grc.tsv"
    path.write_text("ἐγώ\tἐγὼ\nἄλλος\tἐγώ\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fold to the same canonical form"):
        dictionary_builder._layer_entries(path, "grc")


def test_override_layer_wins_base(tmp_path, monkeypatch) -> None:
    _layers(tmp_path, monkeypatch, overrides="overridden\tcats\nnew\tnews\n")
    base = {"dogs": "dog", "cats": "cat"}
    out = dictionary_builder._compose_from_base(base, "zz")
    assert out["dogs"] == "dog"
    assert out["cats"] == "overridden"
    assert out["news"] == "new"


def test_scrub_drops_unreachable_keys_and_fixes_junk_values() -> None:
    d = {
        "dogs": "dog",
        "\ufeff" + "cat": "cat",  # BOM key: unreachable -> dropped
        "as": "\ufeff" + "a",  # BOM in value: normalized to clean lemma
        "hithau": "prpers",  # template placeholder value -> dropped
        "Andre" + "\u0306" + "as": "andreas",  # decomposed key -> dropped
        "don\u2019t": "do",  # curly-quote key: not normalize_token-stable -> dropped
        "Alssund": "Als Sund",  # spaced value: multi-word output never ships
    }
    out = dictionary_builder._scrub(d)
    assert out == {"dogs": "dog", "as": "a"}


def test_shipped_dict_folds_keys_and_rejects_twins(monkeypatch) -> None:
    """Shipped keys fold to runtime form, and twins with different values fail."""
    entries = {"\u03c0\u03b1\u03c1\u2019".encode(): "\u03c0\u03b1\u03c1\u03ac".encode()}
    monkeypatch.setattr(
        dictionary_builder, "_load_dictionary_from_disk", lambda lang: entries
    )
    assert dictionary_builder._shipped_str_dict("zz") == {
        "\u03c0\u03b1\u03c1'": "\u03c0\u03b1\u03c1\u03ac"
    }
    entries[b"can't"], entries["can\u2019t".encode()] = b"cannot", b"can"
    with pytest.raises(ValueError, match="folds to"):
        dictionary_builder._shipped_str_dict("zz")


def test_curly_quote_override_form_survives(tmp_path) -> None:
    """A curly-apostrophe override form folds to the straight key, not dropped."""
    assert dictionary_builder._scrub(_layer(tmp_path, "do\tdon\u2019t\n")) == {
        "don't": "do"
    }


def test_key_alias_renormalizes_stacked_diacritics() -> None:
    """An alias with a stranded combining mark is re-normalized to NFC."""
    out = dictionary_builder._apply_build_normalization({"Boō̈tēs": "Bootes"}, "la")
    assert "Boötes" in out
    assert all(dictionary_builder._valid_key(k) for k in out)


def test_compose_restores_override_entries_from_junk_filter(
    tmp_path, monkeypatch, caplog
) -> None:
    """Reviewed overrides outrank the junk filters, machine rows still drop."""
    overrides = tmp_path / "overrides"
    overrides.mkdir()
    (overrides / "bg.tsv").write_text("втори\tII\n", encoding="utf-8")
    base = {"радост": "радост", "rádost": "радост"}  # machine transliteration row
    with caplog.at_level(logging.INFO, logger=dictionary_builder.LOGGER.name):
        out = dictionary_builder._compose_from_base(base, "bg", overrides_dir=overrides)
    assert out["II"] == "втори"
    assert "rádost" not in out
    assert "restored 1 reviewed override entries" in caplog.text


def test_clean_base_drops_junk_keys_keeps_values() -> None:
    d = {
        "dogs": "dog",
        "-la": "\u00e9l",  # leading-hyphen key (affix fragment) -> dropped
        "astro-": "astro-",  # trailing-hyphen key -> dropped
        "a_b": "ab",  # underscore key -> dropped
        "Alssund": "Als Sund",  # spaced value passes here, _scrub drops it later
    }
    out = dictionary_builder._clean_base(d)
    assert out == {"dogs": "dog", "Alssund": "Als Sund"}


def test_scrub_drops_affix_values_keeps_identities() -> None:
    d = {
        "schaft": "-schaft",  # non-identity affix value -> dropped
        "astro": "astro-",  # trailing-hyphen value -> dropped
        "?": ";",  # non-identity no-alpha value -> dropped
        ":": "на",  # symbol form -> word value (mined noise) -> dropped
        "&": "&",  # identity: kept (is_known contract)
        "10": "10",  # identity number: kept
    }
    out = dictionary_builder._scrub(d)
    assert out == {"&": "&", "10": "10"}


def test_read_dict_rule_mismatch_logged(tmp_path, caplog) -> None:
    """A rule vs list lemma mismatch logs at DEBUG only."""
    fixture = tmp_path / "de.txt"
    # rule("Bäckerei") == "Bäckerei", but the list gives a different lemma.
    fixture.write_text("baeckerei\tBäckerei\n", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger=wordlist_ingest.LOGGER.name):
        wordlist_ingest.read_wordlist(fixture, "de")
    assert "Bäckerei" in caplog.text and "rule mismatch" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO, logger=wordlist_ingest.LOGGER.name):
        wordlist_ingest.read_wordlist(fixture, "de")
    assert "rule mismatch" not in caplog.text


def test_lemmatizes_language_built_from_wordlist(tmp_path) -> None:
    raw = {
        k.encode(): v.encode()
        for k, v in _read(tmp_path, "zz", "dog\tdogs\ncat\tcats\n").items()
    }

    class WordlistFactory(DictionaryFactory):
        def get_dictionary(self, lang: str) -> MappingStrToByteString:
            return MappingStrToByteString(raw)

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=WordlistFactory())
    )
    assert lemmatizer.lemmatize("dogs", lang="zz") == "dog"
    assert lemmatizer.lemmatize("xyz", lang="zz") == "xyz"


def test_generated_plzma_loads_through_real_reader(tmp_path, monkeypatch) -> None:
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\n")
    raw = dictionary_factory._load_dictionary_from_disk("zz")
    assert raw == {b"dog": b"dog", b"dogs": b"dog", b"cat": b"cat", b"cats": b"cat"}

    class GeneratedFactory(DictionaryFactory):
        def get_dictionary(self, lang: str) -> MappingStrToByteString:
            return MappingStrToByteString(raw)

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=GeneratedFactory())
    )
    assert lemmatizer.lemmatize("dogs", lang="zz") == "dog"


def test_build_default_composes_over_shipped_dict(tmp_path, monkeypatch) -> None:
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\n")
    # cats collides, birds is new
    _layers(tmp_path, monkeypatch, overrides="CAT\tcats\nbird\tbirds\n")

    built = tmp_path / "out.plzma"
    dictionary_builder._build_dictionary("zz", filepath=str(built))
    result = _fc_decode(built.read_bytes())
    assert result[b"dogs"] == b"dog"
    assert result[b"cats"] == b"CAT"
    assert result[b"birds"] == b"bird"


def test_build_wordlist_ingestion_keeps_curated_mappings(tmp_path, monkeypatch) -> None:
    """Precedence is override, shipped, then list, so re-extraction only adds."""
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\nmouse\tmice\n")
    _layers(tmp_path, monkeypatch, overrides="RODENT\tmice\n")

    (tmp_path / "fresh").mkdir()
    (tmp_path / "fresh" / "zz.txt").write_text(
        "WRONGDOG\tdogs\nbird\tbirds\n", encoding="utf-8"
    )
    built = tmp_path / "out.plzma"
    wordlist_ingest.ingest("zz", tmp_path / "fresh", filepath=str(built))
    result = _fc_decode(built.read_bytes())
    assert result[b"dogs"] == b"dog"  # shipped beats the re-extraction
    assert result[b"mice"] == b"RODENT"  # override beats shipped
    assert result[b"birds"] == b"bird"


def test_build_dictionary_rejects_unshipped_language_without_wordlist(
    tmp_path,
) -> None:
    with pytest.raises(ValueError, match="no shipped dictionary"):
        dictionary_builder._build_dictionary("zz", filepath=str(tmp_path / "out.plzma"))


def test_build_dictionary_is_deterministic(tmp_path) -> None:
    (tmp_path / "zz.txt").write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    a, b = tmp_path / "a.plzma", tmp_path / "b.plzma"
    wordlist_ingest.ingest("zz", tmp_path, filepath=str(a))
    wordlist_ingest.ingest("zz", tmp_path, filepath=str(b))
    assert a.read_bytes() == b.read_bytes()


def test_build_from_shipped_scrubs_placeholder(tmp_path, monkeypatch) -> None:
    raw = {b"hithau": b"prpers", b"dogs": b"dog"}
    (tmp_path / "zz.plzma").write_bytes(_fc_encode(raw))
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset({"zz"}))
    _layers(tmp_path, monkeypatch)
    out = tmp_path / "out.plzma"
    dictionary_builder._build_dictionary("zz", filepath=str(out))
    # the dog selfmap comes from _ensure_value_selfmaps
    assert _fc_decode(out.read_bytes()) == {b"dogs": b"dog", b"dog": b"dog"}


def test_drifted_languages_detects_pipeline_drift(tmp_path, monkeypatch) -> None:
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\n")
    _layers(tmp_path, monkeypatch)
    assert dictionary_builder._drifted_languages(["zz"]) == []
    _layers(tmp_path, monkeypatch, overrides="hound\tdogs\n")
    assert dictionary_builder._drifted_languages(["zz"]) == ["zz"]


def test_ingest_gate_blocks_a_regression(tmp_path, monkeypatch) -> None:
    from training import ud_conllu

    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\n")
    _layers(tmp_path, monkeypatch)
    splits = tmp_path / "splits"
    splits.mkdir()
    (splits / "zz_x-ud-train.conllu").write_text(
        "1\tcats\tcat\tNOUN\t_\t_\t0\troot\t_\t_\n"
        "2\tcat\tcat\tNOUN\t_\t_\t0\troot\t_\t_\n\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ud_conllu, "UD_SPLITS", splits)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    out = tmp_path / "out.plzma"

    (fresh / "zz.txt").write_text("cat\tcats\n", encoding="utf-8")  # improves
    wordlist_ingest.ingest("zz", fresh, filepath=str(out), gate=True)
    assert _fc_decode(out.read_bytes())[b"cats"] == b"cat"

    (fresh / "zz.txt").write_text("dog\tcat\n", encoding="utf-8")  # cat -> dog
    with pytest.raises(RuntimeError, match="gate FAILED"):
        wordlist_ingest.ingest(
            "zz", fresh, filepath=str(tmp_path / "no.plzma"), gate=True
        )
    assert not (tmp_path / "no.plzma").exists()
