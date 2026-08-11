import logging
from pathlib import Path

import pytest

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory
from simplemma.strategies.dictionaries import dictionary_factory
from training.frontcode_encode import _decode as _fc_decode, _encode as _fc_encode
from simplemma.strategies.dictionaries.dictionary_factory import MappingStrToByteString
from training import build_lang_config, dictionary_builder

TEST_DIR = Path(__file__).parent


def _read(tmp_path, lang: str, text: str) -> dict[str, str]:
    """Write a TSV fixture and return the parsed dictionary."""
    fixture = tmp_path / f"{lang}.txt"
    fixture.write_text(text, encoding="utf-8")
    return dictionary_builder._read_dict(fixture, lang)


def _make_shipped(tmp_path, monkeypatch, text: str) -> None:
    """Build a zz.plzma and install it as the shipped dict (DATA_FOLDER -> tmp_path)."""
    (tmp_path / "zz.txt").write_text(text, encoding="utf-8")
    dictionary_builder._build_dictionary(
        "zz", listpath=str(tmp_path), filepath=str(tmp_path / "zz.plzma")
    )
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset({"zz"}))


def _layers(
    tmp_path, monkeypatch, *, fill: str | None = None, overrides: str | None = None
):
    """Point FILL_DIR/OVERRIDES_DIR at tmp dirs, writing the given zz.tsv
    (lemma<TAB>form) text. A None layer points at a missing dir (no layer)."""
    for kind, text, attr in (
        ("fill", fill, "FILL_DIR"),
        ("overrides", overrides, "OVERRIDES_DIR"),
    ):
        directory = tmp_path / kind
        if text is not None:
            directory.mkdir(exist_ok=True)
            (directory / "zz.tsv").write_text(text, encoding="utf-8")
        monkeypatch.setattr(dictionary_builder, attr, directory)
    if fill is not None:  # allowlist the test language for the fill layer
        monkeypatch.setattr(
            dictionary_builder,
            "V2_FILL_LANGS",
            dictionary_builder.V2_FILL_LANGS | {"zz"},
        )


def test_logic(tmp_path, monkeypatch) -> None:
    # 6 entries: 1-char-lemma pair (s/st) kept -- min-lemma floor is just non-empty now
    mydict = dictionary_builder._read_dict(TEST_DIR / "data/zz.txt", "zz")
    assert len(mydict) == 6

    listpath = str(TEST_DIR / "data")
    temp_outputfile = str(tmp_path / "zz.plzma")
    dictionary_builder._build_dictionary("zz", listpath, temp_outputfile)
    roundtripped = _fc_decode(Path(temp_outputfile).read_bytes())
    assert isinstance(roundtripped, dict)
    assert len(roundtripped) == 6
    assert all(isinstance(k, bytes) for k in roundtripped)

    # in_place=True writes into DATA_FOLDER; point it at tmp_path so a crash can't
    # leave a stray zz.plzma in the real package data. Patch the factory module,
    # since dictionary_builder reads DATA_FOLDER from it at call time.
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    dictionary_builder._build_dictionary("zz", listpath, in_place=True)
    assert (tmp_path / "zz.plzma").exists()


def test_read_dict_filtering(tmp_path) -> None:
    """Valid pair + identity, punctuation drop (either field), length-difference
    drop, conflict resolution."""
    result = _read(
        tmp_path,
        "en",
        "dog\tdogs\n"
        "foo,bar\tbaz\n"  # comma in lemma -> dropped
        "new york\tnyc\n"  # space in lemma -> dropped (not a single token)
        "good\t-bad\n"  # leading-hyphen FORM -> dropped (per-field punct check)
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
    }  # 'good'/'-bad' contribute nothing: the whole line is skipped pre-collect


def test_read_dict_order_independent(tmp_path) -> None:
    """The same line set produces the same dictionary in any line order."""
    lines = ["de\tde\n", "een\tde\n", "dog\tdogs\n"]
    forward = _read(tmp_path, "de", "".join(lines))
    reverse = _read(tmp_path, "de", "".join(reversed(lines)))
    assert forward == reverse


def test_read_dict_attested_identity_beats_lone_challenger(tmp_path) -> None:
    """A single stray line cannot overwrite an explicitly attested identity."""
    result = _read(tmp_path, "de", "de\tde\neen\tde\n")
    assert result["de"] == "de"


def test_read_dict_attestation_count_beats_distance(tmp_path) -> None:
    """Attestation count wins the conflict even against a closer edit distance."""
    result = _read(
        tmp_path,
        "en",
        "run\trunning\n" * 2 + "runninx\trunning\n",
    )
    assert result["running"] == "run"


def test_ensure_value_selfmaps() -> None:
    """Every value gains an identity self-map unless it's already a key,
    unreachable as a token, or letterless; existing keys are never touched."""
    from training.dictionary_builder import _ensure_value_selfmaps

    result = _ensure_value_selfmaps(
        {
            "dogs": "dog",  # missing lemma -> self-map added
            "cats": "cat",
            "cat": "kitten",  # 'cat' already a key -> its mapping stands
            "als": "Als Sund",  # space: unreachable, no self-map
            "x1": "123",  # letterless value, no self-map
        }
    )
    assert result["dog"] == "dog"
    assert result["kitten"] == "kitten"  # value of an existing key still covered
    assert result["cat"] == "kitten"  # not overwritten
    assert "Als Sund" not in result
    assert "123" not in result


def test_read_dict_paradigm_prior_breaks_ties(tmp_path) -> None:
    """For PARADIGM_PRIOR_LANGS, an attestation tie goes to the lemma with the
    larger attested paradigm, not the closer edit distance (grc ἦν: εἰμί and
    ἠμί tie 2-2 in the source; distance alone picks the rare ἠμί)."""
    lines = "εἰμί\tἦν\n" * 2 + "ἠμί\tἦν\n" * 2 + "εἰμί\tἐστί\nεἰμί\tἦσαν\n"
    assert _read(tmp_path, "grc", lines)["ἦν"] == "εἰμί"
    # same shape in an unregistered language keeps the distance tie-break
    lines = "abcd\tab\n" * 2 + "abx\tab\n" * 2 + "abcd\tabcde\nabcd\tabcdf\n"
    assert _read(tmp_path, "en", lines)["ab"] == "abx"


def test_read_dict_lemma_headword_never_reduces(tmp_path) -> None:
    """A word attested as a lemma is forced to itself even if also mapped as a form
    elsewhere; a word only ever a form still reduces. Language-independent
    (formerly the per-language BUFFER_HACK set; gate-confirmed net-positive)."""
    result = _read(tmp_path, "en", "lansa\tlansat\nlansat\tlansare\n")
    assert result["lansat"] == "lansat"  # 'lansat' is a lemma -> itself
    assert result["lansare"] == "lansat"  # 'lansare' only ever a form -> reduces


def test_read_dict_soft_identity_for_grc(tmp_path) -> None:
    """grc is in IDENTITY_SOFT_LANGS: a word that's BOTH a lemma headword and a
    well-attested form of another lemma keeps the attested mapping (participle
    ἀκούσας is both its own headword and a form of ἀκούω) -- unlike the
    universal force-identity behavior (see test_read_dict_lemma_headword_never_reduces)."""
    result = _read(tmp_path, "grc", "ἀκούω\tἀκούσας\n" * 5 + "ἀκούσας\tἀκούσας\n")
    assert result["ἀκούσας"] == "ἀκούω"  # attested mapping wins, not forced to self


def test_read_dict_self_only_lemma_is_soft(tmp_path) -> None:
    """A lemma attested ONLY by its own identity line softens universally
    (attested mapping wins); a paradigm-heading lemma still force-identities.
    This replaced ar's IDENTITY_SOFT_LANGS entry (deleted at +0.000pp)."""
    al_headword = "كتاب\tالكتاب\n" * 5 + "الكتاب\tالكتاب\n"  # self-only lemma
    non_al_headword = "قلم\tبيت\n" * 5 + "بيت\tبيوت\n"  # بيت heads a paradigm
    result = _read(tmp_path, "ar", al_headword + non_al_headword)
    assert result["الكتاب"] == "كتاب"  # soft: attested mapping wins
    assert result["بيت"] == "بيت"  # paradigm-heading: force-identity holds


def test_read_dict_rejects_maqaf_edged_fields(tmp_path) -> None:
    """Hebrew maqaf (U+05BE) is Wiktionary's hyphen for bound-morpheme
    headwords: a line with an edge-maqaf field must be dropped like its
    ASCII-hyphen twin, or frequent fused forms ship garbage values (בו -> ב־)."""
    result = _read(
        tmp_path,
        "he",
        "ב־\tבו\n"  # maqaf-edged LEMMA -> line dropped
        "כלב\tכלבים\n",
    )
    assert "בו" not in result  # not mapped to the ב־ fragment
    assert result["כלבים"] == "כלב"


def test_read_dict_canonicalizes_grc_accents(tmp_path) -> None:
    """grc keys/values are canonicalized grave->acute at the same choke point
    as NFC, so a grave-accented wordlist line ships under its acute key --
    matching what canonicalize_token applies to runtime lookups."""
    result = _read(tmp_path, "grc", "ἐγώ\tἐγὼ\n")
    assert result == {"ἐγώ": "ἐγώ"}  # grave form folded to the acute key


def test_add_key_aliases_ar_hamza() -> None:
    """ar: a hamza-seat/alef-maqsura key gets a folded-key ALIAS pointing at
    the same (correctly spelled) value -- unlike canonicalize_token, the
    value is never touched, so output stays correctly spelled."""
    table = build_lang_config.BUILD_NORMALIZATION["ar"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases({"أحمد": "أحمد", "بيت": "بيت"}, table)
    assert result["احمد"] == "أحمد"  # alias key -> the properly-spelled value
    assert result["أحمد"] == "أحمد"  # original key untouched
    assert "بيت" in result and "بىت" not in result  # no hamza/maqsura: no alias added


def test_add_key_aliases_never_overwrites_an_existing_exact_key() -> None:
    """A folded key that's ALSO a real, independently-attested entry keeps
    its own value -- the alias must never shadow it."""
    table = build_lang_config.BUILD_NORMALIZATION["ar"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"أمن": "أمن", "امن": "امن_different_word"}, table
    )
    assert result["امن"] == "امن_different_word"  # exact entry wins over the alias


def test_add_key_aliases_ru_yo() -> None:
    """ru: a ё-spelled key gains an е-spelled twin (real text writes е for ё),
    value untouched; an existing е-spelled entry always wins (все/всё are
    distinct lemmas and must never merge)."""
    table = build_lang_config.BUILD_NORMALIZATION["ru"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"ребёнка": "ребёнок", "всё": "всё", "все": "весь"}, table
    )
    assert result["ребенка"] == "ребёнок"  # alias key -> the ё-spelled value
    assert result["все"] == "весь"  # real е-entry wins over всё's alias


def test_add_key_aliases_hbs_pitch_marks() -> None:
    """hbs: a pitch/length-marked key gains a plain-spelled twin (real text
    never types the marks); an existing plain entry always wins. The raw
    function defaults to ADD (both keys survive) -- drop_original is a
    separate, explicit opt-in (see test_add_key_aliases_drop_original)."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases(
        {"Hr̀vātskā": "Hrvatska", "vȉde": "vidjeti", "vide": "videti"}, table
    )
    assert result["Hrvatska"] == "Hrvatska"  # alias from the marked key
    assert result["vide"] == "videti"  # real plain entry wins over vȉde's alias
    assert "Hr̀vātskā" in result  # ADD (default): marked original survives too


def test_add_key_aliases_drop_original() -> None:
    """drop_original=True REPLACES the marked key with its plain form instead
    of keeping both -- the shipped hbs/fa/bg/uk/lt/sl/la behavior. A real
    plain entry still always wins (never overwritten), and the marked
    original is gone either way."""
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
    """ś/ź (real Montenegrin letters) must survive the pitch fold's keep=,
    like ć -- else dośetka/źenica get corrupted."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].key_alias
    assert table is not None
    for ch in "śŚźŹ":
        assert ch.translate(table) == ch  # untouched, like ć/Ć
    result = dictionary_builder._apply_build_normalization(
        {"dośetka": "dośetka", "źenica": "źenica"}, "hbs"
    )
    assert result == {"dośetka": "dośetka", "źenica": "źenica"}


def test_apply_build_normalization_hbs_drops_marked_originals() -> None:
    """End-to-end: BUILD_NORMALIZATION["hbs"].drop_folded_keys is wired
    through _apply_build_normalization, not just the raw function default."""
    result = dictionary_builder._apply_build_normalization(
        {"Hr̀vātskā": "Hrvatska"}, "hbs"
    )
    assert result == {"Hrvatska": "Hrvatska"}


def test_apply_build_normalization_ru_keeps_original() -> None:
    """ru's ё is genuinely typed in real text -- ru must NOT drop the
    original, unlike hbs/fa/bg/uk/lt/sl/la."""
    result = dictionary_builder._apply_build_normalization({"ребёнка": "ребёнок"}, "ru")
    assert result == {"ребёнка": "ребёнок", "ребенка": "ребёнок"}


def test_fix_value_scripts_hbs() -> None:
    """A Latin key never keeps a Cyrillic value (deterministic Cyr->Lat
    transliteration); Cyrillic and mixed-script keys stay untouched, and a
    value with non-Serbian Cyrillic is left whole, not half-transliterated."""
    table = build_lang_config.BUILD_NORMALIZATION["hbs"].value_script_fix
    assert table is not None
    result = dictionary_builder._fix_value_scripts(
        {
            "Milorad": "Милорад",  # fixed
            "jun": "јун",  # fixed
            "Милорад": "Милорад",  # Cyrillic key: untouched
            "atoмска": "атомски",  # mixed-script key: untouched
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
    """A mark-only key (kept by _scrub's identity exemption) folds to "" under
    fa's deletion table -- the empty alias must be skipped, not added."""
    table = build_lang_config.BUILD_NORMALIZATION["fa"].key_alias
    assert table is not None
    result = dictionary_builder._add_key_aliases({"ـ": "ـ"}, table)
    assert result == {"ـ": "ـ"}  # no "" key


def test_apply_build_normalization_noop_for_unregistered_langs() -> None:
    d = {"أحمد": "أحمد"}
    assert dictionary_builder._apply_build_normalization(d, "zz") == d


def test_drop_junk_keys_uk_paradigm_codes() -> None:
    """uk: Wiktionary conjugation-table paradigm-class codes and footnote
    leaks are dropped -- no real Ukrainian word starts with a digit."""
    result = dictionary_builder._drop_junk_keys(
        {"10a": "вибороти", "¹Rare.": "літ", "мати": "мати"}, "uk"
    )
    assert result == {"мати": "мати"}


def test_drop_junk_keys_uk_latin_homoglyphs() -> None:
    """uk: a key mixing Latin and Cyrillic letters is a homoglyph-poisoned
    row ('cказився' with Latin c -- 15,870 shipped entries, none with a
    legitimate multi-letter Latin segment)."""
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
    """grc drops English gloss values (κάλαμος -> plants), the wholly-Latin
    identity selfmaps they seed, and Beta-code keys; Greek->Greek stays."""
    result = dictionary_builder._drop_junk_keys(
        {"κάλαμος": "plants", "plants": "plants", "hubrisin": "ὑβρίς", "ἦν": "εἰμί"},
        "grc",
    )
    assert result == {"ἦν": "εἰμί"}


def test_drop_junk_keys_wholly_foreign_identity() -> None:
    """Wholly-foreign identity rows drop in uk/ar/hi; bg keeps its legitimate
    Latin currency abbreviations and he its Phoenician attestations --
    both measured exclusions."""
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
    """An identity key planted for a junk VALUE is still filtered -- whether
    the key trips the predicate itself (uk homoglyph) or only as a pair
    (grc Latin gloss, via _is_wholly_foreign_entry)."""
    # uk: value carries a Latin homoglyph and is not itself a key
    planted = dictionary_builder._ensure_value_selfmaps({"мати": "cказився"})
    assert planted["cказився"] == "cказився"  # selfmap planted
    # the planted key is filtered; the clean-keyed original entry stays
    assert dictionary_builder._drop_junk_keys(planted, "uk") == {"мати": "cказився"}
    # grc: the gloss pair AND the identity key it seeded are both dropped
    planted = dictionary_builder._ensure_value_selfmaps({"κάλαμος": "plants"})
    assert planted["plants"] == "plants"
    assert dictionary_builder._drop_junk_keys(planted, "grc") == {}


def test_drop_junk_keys_noop_for_other_langs() -> None:
    """A digit-leading key is a REAL word in many languages (da, de, en, ga,
    hu, sv all ship one) -- the filter must never apply outside its
    verified-junk-only language."""
    d = {"10a": "10a", "1000ú": "1000ú"}
    assert dictionary_builder._drop_junk_keys(d, "ga") == d


def test_drop_junk_keys_tl_baybayin() -> None:
    """tl: Baybayin-script keys (alt_of leaks) are dropped key-side --
    including the handful whose VALUES are also Baybayin, which a foreign-
    script (value-checking) test would miss. Latin entries untouched."""
    result = dictionary_builder._drop_junk_keys(
        {"ᜀᜀᜃᜓᜀ": "akuin", "ᜇ": "ᜇ", "akuin": "akuin"}, "tl"
    )
    assert result == {"akuin": "akuin"}


def test_drop_junk_keys_he_latin_transliterations() -> None:
    """he: a Latin key resolving to a Hebrew value is transliteration noise;
    Hebrew keys (and non-alphabetic keys) are untouched."""
    result = dictionary_builder._drop_junk_keys(
        {"Slitherin": "סלית׳רין", "בית": "בית", "3": "3"}, "he"
    )
    assert result == {"בית": "בית", "3": "3"}


def _foreign_script_key(key: str, value: str, allowed: frozenset[str]) -> bool:
    """String-level adapter: the real predicate takes precomputed script sets
    (_drop_junk_keys computes them once per entry)."""
    return build_lang_config._foreign_script_key(
        dictionary_builder._script_classes(key),
        dictionary_builder._script_classes(value),
        allowed,
    )


_FOREIGN_SCRIPT_KEY_CASES = [
    # ar IPA transcription: key entirely outside the allowed script → drop
    pytest.param("uð.ðu.ki.ruː", "اذكروا", frozenset({"ARABIC"}), True, id="ar-ipa"),
    # grc Beta-code romanization → drop
    pytest.param(
        "hubrisin",
        "ὑβρίς",
        frozenset({"GREEK", "CYPRIOT", "LINEAR"}),
        True,
        id="grc-betacode",
    ),
    # grc Cypriot-syllabary: a real alternate script, not noise → keep
    pytest.param(
        "𐠞𐠪𐠐𐠄𐠩",
        "βασιλεύς",
        frozenset({"GREEK", "CYPRIOT", "LINEAR"}),
        False,
        id="grc-cypriot-kept",
    ),
    # ms Jawi→Rumi direction is correct → keep
    pytest.param("جون", "Jun", frozenset({"ARABIC"}), False, id="ms-jawi-to-rumi"),
    # ms Rumi→Jawi direction is the defect → drop
    pytest.param("pintu", "ڤينتو", frozenset({"ARABIC"}), True, id="ms-rumi-to-jawi"),
    # mixed-script key (Latin+Cyrillic): never flagged
    pytest.param(
        "atoмска",
        "атомски",
        frozenset({"CYRILLIC"}),
        False,
        id="mixed-script",
    ),
    # purely non-alphabetic key (digits): no script class → never flagged
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
    """hi: Wiktionary's shared Hindi/Urdu extraction leaks Perso-Arabic-
    script entries; Urdu isn't a supported language and real Hindi text is
    always Devanagari."""
    result = dictionary_builder._drop_junk_keys({"سفید": "सफ़ेद", "सफ़ेद": "सफ़ेद"}, "hi")
    assert result == {"सफ़ेद": "सफ़ेद"}


def test_drop_junk_keys_ms_keeps_jawi_to_rumi_direction() -> None:
    result = dictionary_builder._drop_junk_keys({"جون": "Jun", "pintu": "ڤينتو"}, "ms")
    assert result == {"جون": "Jun"}


def test_build_dictionary_ships_ar_hamza_alias(tmp_path, monkeypatch) -> None:
    """End-to-end: a wordlist entry with a hamza-seat form ships both its own
    key and the folded-key alias in the built .plzma."""
    # ar ships for real -- unlist it so ingestion doesn't layer the real dict
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset())
    listpath = str(tmp_path)
    (tmp_path / "ar.txt").write_text("أحمد\tأحمد\n", encoding="utf-8")
    outfile = str(tmp_path / "ar.plzma")
    dictionary_builder._build_dictionary("ar", listpath, outfile)
    built = _fc_decode(Path(outfile).read_bytes())
    assert built["أحمد".encode()] == "أحمد".encode()  # original key
    assert built["احمد".encode()] == "أحمد".encode()  # folded-key alias


def test_read_dict_keeps_long_and_single_char_entries(tmp_path) -> None:
    """No length cap (VOC_LIMIT/MAXLENGTH gone) and no per-language min-lemma
    exemption (SAFE_LIMIT collapsed): long forms and 1-char lemmas are kept."""
    result = _read(
        tmp_path,
        "fi",
        "pitkä\tpitkänmatkanjuoksija\no\to\n",  # long form; 1-char lemma
    )
    assert result["pitkänmatkanjuoksija"] == "pitkä"
    assert result["o"] == "o"


def test_read_dict_normalizes_to_nfc(tmp_path) -> None:
    """Keys/values are NFC -- runtime lookups NFC-normalize, so non-NFC keys would never match."""
    decomposed = "café"  # e + combining acute (NFD)
    result = _read(tmp_path, "en", f"{decomposed}\t{decomposed}s\n")
    assert result == {"café": "café", "cafés": "café"}


def test_read_dict_rejects_control_and_mojibake_keys(tmp_path) -> None:
    """Rejected even if clean_wordlist was skipped (check_field, not the punct filter, catches them)."""
    result = _read(tmp_path, "en", "dog\tdogs\nbad\tba\x01d\nx\tw�rd\n")
    assert result == {"dog": "dog", "dogs": "dog"}  # \x01 and U+FFFD lines gone


def test_apply_layers_drops_spaced_forms(tmp_path, monkeypatch) -> None:
    """Multi-word layer forms are unreachable keys (tokenizer never yields a spaced token)."""
    _layers(tmp_path, monkeypatch, fill="top hat\ttop hats\ncat\tcats\n")
    merged = dictionary_builder._apply_layers({}, "zz", {})
    assert merged == {"cats": "cat"}  # 'top hats' dropped (space in form)


def test_apply_layers_rejects_junk_entries(tmp_path, monkeypatch) -> None:
    """A curated layer file with mojibake/control chars fails the build loud, not a silent skip."""
    _layers(tmp_path, monkeypatch, fill="good\tgoods\nbad\tba\x01d\n")
    with pytest.raises(ValueError, match="rejected"):
        dictionary_builder._apply_layers({}, "zz", {})


def test_apply_layers_rejects_empty_fields(tmp_path, monkeypatch) -> None:
    """An empty lemma/form in a curated layer fails the build rather than shipping a '' key."""
    _layers(tmp_path, monkeypatch, fill="good\tgoods\nlemma\t\n")
    with pytest.raises(ValueError, match="empty"):
        dictionary_builder._apply_layers({}, "zz", {})


def test_layer_entries_canonicalizes_a_grc_override(tmp_path) -> None:
    """An override line with a grave-accented (non-canonical) form/lemma
    ships under its acute key -- the same fold _collect_candidates applies
    to the base wordlist, so a reviewed layer file can't ship a dead key
    (the exact bug build_override.py's mining side hit once by folding only
    the lemma column by hand)."""
    path = tmp_path / "grc.tsv"
    path.write_text("ἐγώ\tἐγὼ\n", encoding="utf-8")
    entries = dictionary_builder._layer_entries(path, "grc")
    assert entries == {"ἐγώ": "ἐγώ"}  # grave form folded to the acute key


def test_layer_entries_rejects_a_canon_collision(tmp_path) -> None:
    """Two override lines that fold to the same canonical form but disagree
    on the lemma must fail the build loud, not silently pick one."""
    path = tmp_path / "grc.tsv"
    path.write_text("ἐγώ\tἐγὼ\nἄλλος\tἐγώ\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fold to the same canonical form"):
        dictionary_builder._layer_entries(path, "grc")


def test_apply_layers_precedence(tmp_path, monkeypatch) -> None:
    """overrides > base > fill: fill only adds, overrides always win."""
    _layers(tmp_path, monkeypatch, fill="filllemma\tdogs\nnew\tnews\n")
    base = {"dogs": "dog", "cats": "cat"}
    merged = dictionary_builder._apply_layers(base, "zz", {"cats": "overridden"})
    assert merged["dogs"] == "dog"  # fill never displaces a base entry
    assert merged["news"] == "new"  # fill adds what's missing
    assert merged["cats"] == "overridden"  # override always wins


def test_apply_layers_without_layer_files_is_identity(tmp_path, monkeypatch) -> None:
    _layers(tmp_path, monkeypatch)  # no fill, no override
    base = {"dogs": "dog"}
    assert dictionary_builder._apply_layers(base, "zz", {}) == base


def test_scrub_drops_unreachable_keys_and_fixes_junk_values() -> None:
    d = {
        "dogs": "dog",  # clean: kept as-is
        "\ufeff" + "cat": "cat",  # BOM key: unreachable -> dropped
        "as": "\ufeff" + "a",  # BOM in value: normalized to clean lemma
        "hithau": "prpers",  # template placeholder value -> dropped
        "Andre" + "\u0306" + "as": "andreas",  # decomposed key -> dropped
        "don\u2019t": "do",  # curly-quote key: reachable (runtime is NFC-only) -> kept
        "Alssund": "Als Sund",  # spaced value: multi-word output never ships
    }
    out = dictionary_builder._scrub(d)
    assert out == {"dogs": "dog", "as": "a", "don\u2019t": "do"}


def test_curly_quote_override_form_survives(tmp_path, monkeypatch) -> None:
    """A typographic-apostrophe override form isn't dropped post-layer (read_pairs and _valid_key agree: NFC-only)."""
    _layers(tmp_path, monkeypatch, overrides="do\tdon\u2019t\n")
    entries = dictionary_builder._layer_entries(
        dictionary_builder.OVERRIDES_DIR / "zz.tsv", "zz"
    )
    out = dictionary_builder._scrub(dictionary_builder._apply_layers({}, "zz", entries))
    assert out == {"don\u2019t": "do"}


def test_key_alias_renormalizes_stacked_diacritics() -> None:
    """The la macron fold on a stacked diacritic strands a combining mark;
    the alias must re-NFC or it ships NFC-invalid and _clean_base kills it
    next rebuild (shipped la 'Boō̈tēs' regression)."""
    out = dictionary_builder._apply_build_normalization({"Boō̈tēs": "Bootes"}, "la")
    assert "Boötes" in out  # precomposed ö, _valid_key-clean
    assert all(dictionary_builder._valid_key(k) for k in out)


def test_compose_restores_override_entries_from_junk_filter(
    tmp_path, monkeypatch, caplog
) -> None:
    """Reviewed override entries outrank the junk predicates: bg 'II' ->
    'втори' is deliberate, while the same shape from a machine source
    (BGN transliteration) still drops."""
    overrides = tmp_path / "overrides"
    overrides.mkdir()
    (overrides / "bg.tsv").write_text("втори\tII\n", encoding="utf-8")
    base = {"радост": "радост", "rádost": "радост"}  # machine translit row
    with caplog.at_level(logging.INFO, logger=dictionary_builder.LOGGER.name):
        out = dictionary_builder._compose_from_base(base, "bg", overrides_dir=overrides)
    assert out["II"] == "втори"  # restored
    assert "rádost" not in out  # machine junk still dropped
    assert "restored 1 reviewed override entries" in caplog.text


def test_clean_base_drops_junk_keys_keeps_values() -> None:
    d = {
        "dogs": "dog",  # clean: kept
        "-la": "\u00e9l",  # leading-hyphen key (affix fragment) -> dropped
        "astro-": "astro-",  # trailing-hyphen key -> dropped
        "a_b": "ab",  # underscore key -> dropped
        "Alssund": "Als Sund",  # spaced VALUE passes here; _scrub drops it post-layer
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
    """A DEFAULT_RULES/list lemma mismatch logs at DEBUG only (opt-in, off by default)."""
    fixture = tmp_path / "de.txt"
    # rule("Bäckerei") == "Bäckerei", but the list gives a different lemma.
    fixture.write_text("baeckerei\tBäckerei\n", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger=dictionary_builder.LOGGER.name):
        dictionary_builder._read_dict(fixture, "de")
    assert "Bäckerei" in caplog.text and "rule mismatch" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO, logger=dictionary_builder.LOGGER.name):
        dictionary_builder._read_dict(fixture, "de")
    assert "rule mismatch" not in caplog.text


def test_lemmatizes_language_built_from_wordlist(tmp_path) -> None:
    """End-to-end: a wordlist-built dict is consumable by the Lemmatizer."""
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
    """A built (front-coded) .plzma loads via the production reader and lemmatizes."""
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
    """A routine rebuild (no wordlist) builds on the decoded shipped dict."""
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\n")
    # override layer: one collision (cats -> CAT) + one new form (birds -> bird)
    _layers(tmp_path, monkeypatch, overrides="CAT\tcats\nbird\tbirds\n")

    built = tmp_path / "out.plzma"
    dictionary_builder._build_dictionary("zz", filepath=str(built))
    result = _fc_decode(built.read_bytes())
    assert result[b"dogs"] == b"dog"  # decoded-shipped base survives
    assert result[b"cats"] == b"CAT"  # override wins the collision
    assert result[b"birds"] == b"bird"  # new form added


def test_build_wordlist_ingestion_keeps_curated_mappings(tmp_path, monkeypatch) -> None:
    """Wordlist ingestion into a shipped language auto-layers the installed
    mappings (override > shipped > list > fill): a re-extraction only ADDS."""
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\nmouse\tmice\n")
    _layers(tmp_path, monkeypatch, fill="FISH\tcats\n", overrides="RODENT\tmice\n")

    # re-extraction: DISAGREES on dogs, adds a new form birds
    (tmp_path / "fresh").mkdir()
    (tmp_path / "fresh" / "zz.txt").write_text(
        "WRONGDOG\tdogs\nbird\tbirds\n", encoding="utf-8"
    )
    built = tmp_path / "out.plzma"
    dictionary_builder._build_dictionary(
        "zz", listpath=str(tmp_path / "fresh"), filepath=str(built)
    )
    result = _fc_decode(built.read_bytes())
    assert result[b"dogs"] == b"dog"  # shipped beats the re-extraction
    assert result[b"cats"] == b"cat"  # shipped beats fill
    assert result[b"mice"] == b"RODENT"  # override beats shipped
    assert result[b"birds"] == b"bird"  # list-only key added


def test_build_dictionary_rejects_unshipped_language_without_wordlist(
    tmp_path,
) -> None:
    """No shipped dict and no wordlist = nothing to build from; fail loud
    instead of writing an empty dictionary."""
    with pytest.raises(ValueError, match="no shipped dictionary"):
        dictionary_builder._build_dictionary("zz", filepath=str(tmp_path / "out.plzma"))


def test_build_dictionary_is_deterministic(tmp_path) -> None:
    """Two builds of the same input produce byte-identical .plzma (trie cache is keyed on shipped bytes)."""
    (tmp_path / "zz.txt").write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    a, b = tmp_path / "a.plzma", tmp_path / "b.plzma"
    dictionary_builder._build_dictionary("zz", listpath=str(tmp_path), filepath=str(a))
    dictionary_builder._build_dictionary("zz", listpath=str(tmp_path), filepath=str(b))
    assert a.read_bytes() == b.read_bytes()


def test_apply_layers_cleans_machine_fill(tmp_path, monkeypatch) -> None:
    """Fill is a machine source: _apply_layers runs _clean_base over it, dropping
    affix-fragment keys, unlike a reviewed override which keeps its elisions."""
    _layers(tmp_path, monkeypatch, fill="-al\t-al\ncat\tcats\n")
    merged = dictionary_builder._apply_layers({}, "zz", {})
    assert merged == {"cats": "cat"}  # '-al' affix key dropped


def test_apply_layers_rejects_unlisted_fill(tmp_path, monkeypatch) -> None:
    """A fill file outside V2_FILL_LANGS fails the build loud: fill/ is gitignored,
    so a stale local TSV must not ship silently against the reviewed decision."""
    fill_dir = tmp_path / "fill"
    fill_dir.mkdir()
    (fill_dir / "fr.tsv").write_text("chat\tchats\n", encoding="utf-8")
    monkeypatch.setattr(dictionary_builder, "FILL_DIR", fill_dir)
    with pytest.raises(ValueError, match="V2_FILL_LANGS"):
        dictionary_builder._apply_layers({}, "fr", {})


def test_build_from_shipped_scrubs_placeholder(tmp_path, monkeypatch) -> None:
    """A pre-v2 shipped dict with a template placeholder value is scrubbed on rebuild."""
    raw = {b"hithau": b"prpers", b"dogs": b"dog"}
    (tmp_path / "zz.plzma").write_bytes(_fc_encode(raw))
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset({"zz"}))
    _layers(tmp_path, monkeypatch)  # no fill, no override
    out = tmp_path / "out.plzma"
    dictionary_builder._build_dictionary("zz", filepath=str(out))
    # b"dog": b"dog" is _ensure_value_selfmaps covering the surviving value
    assert _fc_decode(out.read_bytes()) == {b"dogs": b"dog", b"dog": b"dog"}
