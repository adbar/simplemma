import logging
from pathlib import Path

import pytest

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory
from simplemma.strategies.dictionaries import dictionary_factory, frontcode
from simplemma.strategies.dictionaries.dictionary_factory import MappingStrToByteString
from training import dictionary_pickler

TEST_DIR = Path(__file__).parent


def _read(tmp_path, lang: str, text: str) -> dict[bytes, bytes]:
    """Write a TSV fixture and return the parsed dictionary."""
    fixture = tmp_path / f"{lang}.txt"
    fixture.write_text(text, encoding="utf-8")
    return dictionary_pickler._read_dict(str(fixture), lang)


def _make_shipped(tmp_path, monkeypatch, text: str) -> None:
    """Build a zz.plzma from a wordlist and install it as the shipped dict
    (DATA_FOLDER -> tmp_path), the arrange shared by the base-mode tests."""
    (tmp_path / "zz.txt").write_text(text, encoding="utf-8")
    dictionary_pickler._build_dictionary(
        "zz", listpath=str(tmp_path), filepath=str(tmp_path / "zz.plzma")
    )
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)


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
        monkeypatch.setattr(dictionary_pickler, attr, directory)


def test_logic(tmp_path, monkeypatch) -> None:
    """Test if certain code parts correspond to the intended logic."""
    testfile = str(TEST_DIR / "data/zz.txt")
    # 6 entries: the 1-char-lemma pair (s/st) is kept now that the per-language
    # min-lemma exemption is collapsed to a uniform "non-empty" floor.
    mydict = dictionary_pickler._read_dict(testfile, "zz")
    assert len(mydict) == 6
    mydict = dictionary_pickler._load_dict("zz", listpath=str(TEST_DIR / "data"))
    assert len(mydict) == 6

    listpath = str(TEST_DIR / "data")
    temp_outputfile = str(tmp_path / "zz.plzma")
    dictionary_pickler._build_dictionary("zz", listpath, temp_outputfile)
    roundtripped = frontcode.decode(Path(temp_outputfile).read_bytes())
    assert isinstance(roundtripped, dict)
    assert len(roundtripped) == 6
    assert all(isinstance(k, bytes) for k in roundtripped)

    # in_place=True writes into DATA_FOLDER; point it at tmp so a crash can't
    # leave a stray zz.plzma in the real package data (SUPPORTED_LANGUAGES is
    # computed from that dir's *.plzma listing). The pickler reads DATA_FOLDER
    # from the factory module at call time, so this is the one patch point.
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    dictionary_pickler._build_dictionary("zz", listpath, in_place=True)
    assert (tmp_path / "zz.plzma").exists()


def test_read_dict_filtering(tmp_path) -> None:
    """Valid pair + identity, punctuation drop (either field), length-difference
    drop, conflict resolution."""
    result = _read(
        tmp_path,
        "en",
        "dog\tdogs\n"
        "foo,bar\tbaz\n"  # comma in lemma -> dropped
        "good\t-bad\n"  # leading-hyphen FORM -> dropped (per-field punct check)
        "a\tverylongword\n"
        "verylonglemma\tx\n"
        "run\trunning\n"
        "xunning\trunning\n",  # tied counts: closer lemma wins
    )
    assert result == {
        b"dog": b"dog",
        b"dogs": b"dog",
        b"run": b"run",
        b"running": b"xunning",
        b"xunning": b"xunning",  # losing a conflict doesn't cost the identity
    }  # 'good'/'-bad' contribute nothing: the whole line is skipped pre-collect


def test_read_dict_order_independent(tmp_path) -> None:
    """The same line set produces the same dictionary in any line order."""
    lines = ["de\tde\n", "een\tde\n", "dog\tdogs\n"]
    forward = _read(tmp_path, "de", "".join(lines))
    reverse = _read(tmp_path, "de", "".join(reversed(lines)))
    assert forward == reverse
    assert forward[b"de"] == b"de"


def test_read_dict_attested_identity_beats_lone_challenger(tmp_path) -> None:
    """A single stray line cannot overwrite an explicitly attested identity."""
    result = _read(tmp_path, "de", "de\tde\neen\tde\n")
    assert result[b"de"] == b"de"


def test_read_dict_attestation_count_beats_distance(tmp_path) -> None:
    """Attestation count wins the conflict even against a closer edit distance."""
    result = _read(
        tmp_path,
        "en",
        "run\trunning\n" * 2 + "runninx\trunning\n",
    )
    assert result[b"running"] == b"run"


def test_read_dict_lemma_headword_never_reduces(tmp_path) -> None:
    """A word attested as a lemma is forced to itself even when a line also maps
    it as a form of something else; a word that is only ever a form still
    reduces. Language-independent (formerly the per-language BUFFER_HACK set);
    gate-confirmed net-positive on every language."""
    result = _read(tmp_path, "en", "lansa\tlansat\nlansat\tlansare\n")
    assert result[b"lansat"] == b"lansat"  # 'lansat' is a lemma -> itself
    assert result[b"lansare"] == b"lansat"  # 'lansare' only ever a form -> reduces


def test_read_dict_keeps_long_and_single_char_entries(tmp_path) -> None:
    """No length cap (former VOC_LIMIT/MAXLENGTH gone) and no per-language
    min-lemma exemption (former SAFE_LIMIT collapsed): long agglutinative
    forms and legitimate 1-char lemmas are both kept for every language."""
    result = _read(
        tmp_path,
        "fi",
        "pitkä\tpitkänmatkanjuoksija\no\to\n",  # long form; 1-char lemma
    )
    assert result["pitkänmatkanjuoksija".encode()] == "pitkä".encode()
    assert result[b"o"] == b"o"


def test_read_dict_normalizes_to_nfc(tmp_path) -> None:
    """Keys/values are NFC regardless of how the input list was prepared --
    runtime lookups NFC-normalize, so non-NFC keys would never match."""
    decomposed = "café"  # e + combining acute (NFD)
    result = _read(tmp_path, "en", f"{decomposed}\t{decomposed}s\n")
    nfc = "café".encode()
    assert result == {nfc: nfc, "cafés".encode(): nfc}


def test_read_dict_rejects_control_and_mojibake_keys(tmp_path) -> None:
    """Mojibake/control-char columns are rejected at the pickler even if the
    optional clean_wordlist stage was skipped (check_field, not the punct
    filter, catches them)."""
    result = _read(tmp_path, "en", "dog\tdogs\nbad\tba\x01d\nx\tw�rd\n")
    assert result == {b"dog": b"dog", b"dogs": b"dog"}  # \x01 and U+FFFD lines gone


def test_apply_layers_drops_spaced_forms(tmp_path, monkeypatch) -> None:
    """Multi-word layer forms are unreachable keys (the tokenizer never yields
    a spaced token) and are dropped."""
    _layers(tmp_path, monkeypatch, fill="top hat\ttop hats\ncat\tcats\n")
    merged = dictionary_pickler._apply_layers({}, "zz")
    assert merged == {b"cats": b"cat"}  # 'top hats' dropped (space in form)


def test_apply_layers_rejects_junk_entries(tmp_path, monkeypatch) -> None:
    """A curated layer file with mojibake/control chars is corruption: the
    build fails loud (read_pairs raises), not a silent skip."""
    _layers(tmp_path, monkeypatch, fill="good\tgoods\nbad\tba\x01d\n")
    with pytest.raises(ValueError, match="rejected"):
        dictionary_pickler._apply_layers({}, "zz")


def test_apply_layers_rejects_empty_fields(tmp_path, monkeypatch) -> None:
    """An empty lemma/form in a curated layer file fails the build rather than
    silently shipping a form->'' or a b'' key."""
    _layers(tmp_path, monkeypatch, fill="good\tgoods\nlemma\t\n")
    with pytest.raises(ValueError, match="empty field"):
        dictionary_pickler._apply_layers({}, "zz")


def test_apply_layers_precedence(tmp_path, monkeypatch) -> None:
    """overrides > base > fill: fill only adds, overrides always win."""
    _layers(
        tmp_path,
        monkeypatch,
        fill="filllemma\tdogs\nnew\tnews\n",
        overrides="overridden\tcats\n",
    )
    base = {b"dogs": b"dog", b"cats": b"cat"}
    merged = dictionary_pickler._apply_layers(base, "zz")
    assert merged[b"dogs"] == b"dog"  # fill never displaces a base entry
    assert merged[b"news"] == b"new"  # fill adds what's missing
    assert merged[b"cats"] == b"overridden"  # override always wins


def test_apply_layers_without_layer_files_is_identity(tmp_path, monkeypatch) -> None:
    _layers(tmp_path, monkeypatch)  # no fill, no override
    base = {b"dogs": b"dog"}
    assert dictionary_pickler._apply_layers(base, "zz") == base


def test_scrub_drops_unreachable_keys_and_fixes_junk_values() -> None:
    d = {
        b"dogs": b"dog",  # clean: kept as-is
        ("\ufeff" + "cat").encode(): b"cat",  # BOM key: unreachable -> dropped
        b"as": ("\ufeff" + "a").encode(),  # BOM in value: normalized to clean lemma
        b"hithau": b"prpers",  # template placeholder value -> dropped
        ("Andre" + "\u0306" + "as").encode(): b"andreas",  # decomposed key -> dropped
        "don\u2019t".encode(): b"do",  # curly-quote key: reachable (runtime is
        # NFC-only, keeps curly quotes) -> kept, not silently dropped
    }
    out = dictionary_pickler._scrub(d)
    assert out == {b"dogs": b"dog", b"as": b"a", "don\u2019t".encode(): b"do"}


def test_curly_quote_override_form_survives(tmp_path, monkeypatch) -> None:
    """A reviewed override form spelled with a typographic apostrophe must not
    be silently dropped post-layer (read_pairs and _valid_key agree: NFC-only)."""
    _layers(tmp_path, monkeypatch, overrides="do\tdon\u2019t\n")
    out = dictionary_pickler._scrub(dictionary_pickler._apply_layers({}, "zz"))
    assert out == {"don\u2019t".encode(): b"do"}


def test_clean_base_drops_junk_keys_keeps_values() -> None:
    d = {
        b"dogs": b"dog",  # clean: kept
        b"-la": "\u00e9l".encode(),  # leading-hyphen key (affix fragment) -> dropped
        b"astro-": b"astro-",  # trailing-hyphen key -> dropped
        b"a_b": b"ab",  # underscore key -> dropped
        b"Alssund": b"Als Sund",  # spaced VALUE is legit -> kept
    }
    out = dictionary_pickler._clean_base(d)
    assert out == {b"dogs": b"dog", b"Alssund": b"Als Sund"}


def test_scrub_drops_affix_values_keeps_identities() -> None:
    d = {
        b"schaft": b"-schaft",  # non-identity affix value -> dropped
        b"astro": b"astro-",  # trailing-hyphen value -> dropped
        b"?": b";",  # non-identity no-alpha value -> dropped
        b":": "на".encode(),  # symbol form -> word value (mined noise) -> dropped
        b"&": b"&",  # identity: kept (is_known contract)
        b"10": b"10",  # identity number: kept
    }
    out = dictionary_pickler._scrub(d)
    assert out == {b"&": b"&", b"10": b"10"}


def test_read_dict_rule_mismatch_logged(tmp_path, caplog) -> None:
    """A DEFAULT_RULES lemma disagreeing with the list logs a DEBUG diagnostic,
    emitted only when DEBUG is enabled (opt-in, off in the default config)."""
    fixture = tmp_path / "de.txt"
    # rule("Bäckerei") == "Bäckerei", but the list gives a different lemma.
    fixture.write_text("baeckerei\tBäckerei\n", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger=dictionary_pickler.LOGGER.name):
        dictionary_pickler._read_dict(str(fixture), "de")
    assert "Bäckerei" in caplog.text and "rule mismatch" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO, logger=dictionary_pickler.LOGGER.name):
        dictionary_pickler._read_dict(str(fixture), "de")
    assert "rule mismatch" not in caplog.text


def test_lemmatizes_language_built_from_wordlist(tmp_path) -> None:
    """End-to-end: a pickler-built bytes-dict is consumable by the Lemmatizer."""
    raw = _read(tmp_path, "zz", "dog\tdogs\ncat\tcats\n")

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


def test_build_base_shipped_composes_over_decoded_dict(tmp_path, monkeypatch) -> None:
    """base='shipped' builds on the decoded shipped dict, not a wordlist rebuild:
    base entries survive, overrides win, new forms are added."""
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\n")
    # override layer: one collision (cats -> CAT) + one new form (birds -> bird)
    _layers(tmp_path, monkeypatch, overrides="CAT\tcats\nbird\tbirds\n")

    built = tmp_path / "out.plzma"
    dictionary_pickler._build_dictionary("zz", filepath=str(built), base="shipped")
    result = frontcode.decode(built.read_bytes())
    assert result[b"dogs"] == b"dog"  # decoded-shipped base survives
    assert result[b"cats"] == b"CAT"  # override wins the collision
    assert result[b"birds"] == b"bird"  # new form added


def test_build_base_merged_keeps_curated_mappings(tmp_path, monkeypatch) -> None:
    """base='merged' precedence override > shipped > fresh > fill: the fresh
    wordlist only ADDS keys, the curated shipped mapping wins shared keys
    (beating both fresh and fill), and a reviewed override beats shipped."""
    _make_shipped(tmp_path, monkeypatch, "dog\tdogs\ncat\tcats\nmouse\tmice\n")
    _layers(tmp_path, monkeypatch, fill="FISH\tcats\n", overrides="RODENT\tmice\n")

    # fresh re-extraction: DISAGREES on dogs, adds a new form birds
    (tmp_path / "fresh").mkdir()
    (tmp_path / "fresh" / "zz.txt").write_text(
        "WRONGDOG\tdogs\nbird\tbirds\n", encoding="utf-8"
    )
    built = tmp_path / "out.plzma"
    dictionary_pickler._build_dictionary(
        "zz", listpath=str(tmp_path / "fresh"), filepath=str(built), base="merged"
    )
    result = frontcode.decode(built.read_bytes())
    assert result[b"dogs"] == b"dog"  # shipped beats the fresh re-extraction
    assert result[b"cats"] == b"cat"  # shipped beats fill
    assert result[b"mice"] == b"RODENT"  # override beats shipped
    assert result[b"birds"] == b"bird"  # fresh-only key added


def test_build_dictionary_rejects_unknown_base(tmp_path) -> None:
    """An unrecognized base mode fails loud rather than silently building fresh."""
    with pytest.raises(ValueError, match="unknown base mode"):
        dictionary_pickler._build_dictionary(
            "zz", filepath=str(tmp_path / "out.plzma"), base="bogus"
        )


def test_build_dictionary_is_deterministic(tmp_path) -> None:
    """Two builds of the same input produce byte-identical .plzma (the trie
    cache is keyed on the shipped bytes, so rebuilds must not drift)."""
    (tmp_path / "zz.txt").write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    a, b = tmp_path / "a.plzma", tmp_path / "b.plzma"
    dictionary_pickler._build_dictionary("zz", listpath=str(tmp_path), filepath=str(a))
    dictionary_pickler._build_dictionary("zz", listpath=str(tmp_path), filepath=str(b))
    assert a.read_bytes() == b.read_bytes()


def test_apply_layers_cleans_machine_fill(tmp_path, monkeypatch) -> None:
    """Fill is a machine source, so _apply_layers runs _clean_base over it: an
    affix-fragment key (-al) is unreachable and dropped, unlike a reviewed
    override which keeps its deliberate elisions."""
    _layers(tmp_path, monkeypatch, fill="-al\t-al\ncat\tcats\n")
    merged = dictionary_pickler._apply_layers({}, "zz")
    assert merged == {b"cats": b"cat"}  # '-al' affix key dropped


def test_build_from_shipped_scrubs_placeholder(tmp_path, monkeypatch) -> None:
    """A pre-v2 shipped dict carrying a template placeholder value is scrubbed
    on rebuild (end-to-end through _build_dictionary, base='shipped')."""
    raw = {b"hithau": b"prpers", b"dogs": b"dog"}
    (tmp_path / "zz.plzma").write_bytes(frontcode.encode(raw))
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    _layers(tmp_path, monkeypatch)  # no fill, no override
    out = tmp_path / "out.plzma"
    dictionary_pickler._build_dictionary("zz", filepath=str(out), base="shipped")
    assert frontcode.decode(out.read_bytes()) == {b"dogs": b"dog"}
