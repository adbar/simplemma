import lzma
import pickle

from pathlib import Path

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory
from simplemma.strategies.dictionaries import dictionary_factory
from simplemma.strategies.dictionaries.dictionary_factory import MappingStrToByteString
from training import dictionary_pickler

TEST_DIR = Path(__file__).parent


def _read(tmp_path, lang: str, text: str) -> dict[bytes, bytes]:
    """Write a TSV fixture and return the parsed dictionary."""
    fixture = tmp_path / f"{lang}.txt"
    fixture.write_text(text, encoding="utf-8")
    return dictionary_pickler._read_dict(str(fixture), lang, silent=True)


def test_logic(tmp_path) -> None:
    """Test if certain code parts correspond to the intended logic."""
    testfile = str(TEST_DIR / "data/zz.txt")
    # 6 entries: the 1-char-lemma pair (s/st) is kept now that the per-language
    # min-lemma exemption is collapsed to a uniform "non-empty" floor.
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=True)
    assert len(mydict) == 6
    mydict = dictionary_pickler._load_dict(
        "zz", listpath=str(TEST_DIR / "data"), silent=True
    )
    assert len(mydict) == 6
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=False)
    assert len(mydict) == 6

    assert dictionary_pickler._determine_path("lists", "de").endswith("de.txt")

    listpath = str(TEST_DIR / "data")
    temp_outputfile = str(tmp_path / "zz.pkl")
    dictionary_pickler._pickle_dict("zz", listpath, temp_outputfile)
    with lzma.open(temp_outputfile, "rb") as f:
        roundtripped = pickle.load(f)
    assert isinstance(roundtripped, dict)
    assert len(roundtripped) == 6
    assert all(isinstance(k, bytes) for k in roundtripped)

    # in_place=True writes into the real package data dir
    dictionary_pickler._pickle_dict("zz", listpath, in_place=True)
    filepath = dictionary_pickler._determine_pickle_path("zz", in_place=True)
    Path(filepath).unlink(missing_ok=True)


def test_read_dict_filtering(tmp_path) -> None:
    """Valid pair + identity, punctuation drop, length-difference drop, conflict."""
    result = _read(
        tmp_path,
        "en",
        "dog\tdogs\n"
        "foo,bar\tbaz\n"
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
    }


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


def test_read_dict_unattested_identity_yields_to_reduction(tmp_path) -> None:
    """A form that is also a lemma elsewhere still reduces if never self-attested."""
    result = _read(tmp_path, "en", "lansa\tlansat\nlansat\tlansare\n")
    assert result[b"lansat"] == b"lansa"
    assert result[b"lansare"] == b"lansat"


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


def test_read_dict_buffer_hack(tmp_path) -> None:
    """BUFFER_HACK forces a lemma identity, overwriting a prior mapping."""
    non_hack = _read(tmp_path, "de", "xx\tbb\nbb\tyy\n")  # de not in BUFFER_HACK
    assert non_hack[b"bb"] == b"xx"
    hack = _read(tmp_path, "et", "xx\tbb\nbb\tyy\n")  # et is in BUFFER_HACK
    assert hack[b"bb"] == b"bb"


def test_read_dict_normalizes_to_nfc(tmp_path) -> None:
    """Keys/values are NFC regardless of how the input list was prepared --
    runtime lookups NFC-normalize, so non-NFC keys would never match."""
    decomposed = "café"  # e + combining acute (NFD)
    result = _read(tmp_path, "en", f"{decomposed}\t{decomposed}s\n")
    nfc = "café".encode()
    assert result == {nfc: nfc, "cafés".encode(): nfc}


def test_read_dict_rejects_control_and_mojibake_keys(tmp_path) -> None:
    """Mojibake/control-char keys are rejected at the pickler even if the
    optional clean_wordlist stage was skipped (INPUT_PUNCT doesn't catch them)."""
    result = _read(tmp_path, "en", "dog\tdogs\nbad\tba\x01d\nx\tw�rd\n")
    assert result == {b"dog": b"dog", b"dogs": b"dog"}  # \x01 and U+FFFD lines gone


def test_apply_layers_drops_spaced_forms(tmp_path, monkeypatch) -> None:
    """Multi-word layer forms are unreachable keys (the tokenizer never yields
    a spaced token) and are dropped."""
    (tmp_path / "fill").mkdir()
    (tmp_path / "fill" / "zz.tsv").write_text(
        "top hat\ttop hats\ncat\tcats\n",
        encoding="utf-8",  # lemma<TAB>form
    )
    monkeypatch.setattr(dictionary_pickler, "FILL_DIR", tmp_path / "fill")
    monkeypatch.setattr(dictionary_pickler, "OVERRIDES_DIR", tmp_path / "nope")
    merged = dictionary_pickler._apply_layers({}, "zz")
    assert merged == {b"cats": b"cat"}  # 'top hats' dropped (space in form)


def test_apply_layers_drops_junk_entries(tmp_path, monkeypatch) -> None:
    """Layer entries with mojibake/control chars are dropped too, mirroring the
    base path's key hygiene (not only NFC + the space filter)."""
    (tmp_path / "fill").mkdir()
    (tmp_path / "fill" / "zz.tsv").write_text(
        "good\tgoods\nbad\tba\x01d\n", encoding="utf-8"  # control char in 2nd form
    )
    monkeypatch.setattr(dictionary_pickler, "FILL_DIR", tmp_path / "fill")
    monkeypatch.setattr(dictionary_pickler, "OVERRIDES_DIR", tmp_path / "nope")
    merged = dictionary_pickler._apply_layers({}, "zz")
    assert merged == {b"goods": b"good"}  # 'ba\x01d' dropped


def test_apply_layers_precedence(tmp_path, monkeypatch) -> None:
    """overrides > base > fill: fill only adds, overrides always win."""
    (tmp_path / "fill").mkdir()
    (tmp_path / "overrides").mkdir()
    # layer files are lemma<TAB>form
    (tmp_path / "fill" / "zz.tsv").write_text(
        "filllemma\tdogs\nnew\tnews\n", encoding="utf-8"
    )
    (tmp_path / "overrides" / "zz.tsv").write_text(
        "overridden\tcats\n", encoding="utf-8"
    )
    monkeypatch.setattr(dictionary_pickler, "FILL_DIR", tmp_path / "fill")
    monkeypatch.setattr(dictionary_pickler, "OVERRIDES_DIR", tmp_path / "overrides")

    base = {b"dogs": b"dog", b"cats": b"cat"}
    merged = dictionary_pickler._apply_layers(base, "zz")
    assert merged[b"dogs"] == b"dog"  # fill never displaces a base entry
    assert merged[b"news"] == b"new"  # fill adds what's missing
    assert merged[b"cats"] == b"overridden"  # override always wins


def test_apply_layers_without_layer_files_is_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(dictionary_pickler, "FILL_DIR", tmp_path / "fill")
    monkeypatch.setattr(dictionary_pickler, "OVERRIDES_DIR", tmp_path / "overrides")
    base = {b"dogs": b"dog"}
    assert dictionary_pickler._apply_layers(base, "zz") == base


def test_read_dict_rule_mismatch_print(tmp_path, capsys) -> None:
    """A DEFAULT_RULES lemma disagreeing with the list prints a diagnostic."""
    # rule("Bäckerei") == "Bäckerei", but the list gives a different lemma.
    _read(tmp_path, "de", "baeckerei\tBäckerei\n")
    assert capsys.readouterr().out == "Bäckerei baeckerei Bäckerei\n"


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
    """A pickled .plzma loads via the production reader and lemmatizes."""
    (tmp_path / "zz.txt").write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    dictionary_pickler._pickle_dict(
        "zz", listpath=str(tmp_path), filepath=str(tmp_path / "zz.plzma")
    )

    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    raw = dictionary_factory._load_dictionary_from_disk("zz")

    class GeneratedFactory(DictionaryFactory):
        def get_dictionary(self, lang: str) -> MappingStrToByteString:
            return MappingStrToByteString(raw)

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=GeneratedFactory())
    )
    assert lemmatizer.lemmatize("dogs", lang="zz") == "dog"


def test_generated_frontcoded_plzma_loads_through_real_reader(
    tmp_path, monkeypatch
) -> None:
    """A front-coded .plzma loads via the production reader and lemmatizes
    identically to the legacy pickle format."""
    (tmp_path / "zz.txt").write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    dictionary_pickler._pickle_dict(
        "zz",
        listpath=str(tmp_path),
        filepath=str(tmp_path / "zz.plzma"),
        use_frontcode=True,
    )

    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    raw = dictionary_factory._load_dictionary_from_disk("zz")
    assert raw == {b"dog": b"dog", b"dogs": b"dog", b"cat": b"cat", b"cats": b"cat"}

    class GeneratedFactory(DictionaryFactory):
        def get_dictionary(self, lang: str) -> MappingStrToByteString:
            return MappingStrToByteString(raw)

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=GeneratedFactory())
    )
    assert lemmatizer.lemmatize("dogs", lang="zz") == "dog"


def test_pickle_dict_frontcode_smaller_than_legacy(tmp_path) -> None:
    """Sanity check: front-coding a realistic-shaped wordlist doesn't grow it."""
    lines = "".join(f"form{i}\tlemma{i % 20}\n" for i in range(500))
    (tmp_path / "zz.txt").write_text(lines, encoding="utf-8")

    legacy_path = tmp_path / "legacy.plzma"
    frontcoded_path = tmp_path / "frontcoded.plzma"
    dictionary_pickler._pickle_dict(
        "zz", listpath=str(tmp_path), filepath=str(legacy_path)
    )
    dictionary_pickler._pickle_dict(
        "zz", listpath=str(tmp_path), filepath=str(frontcoded_path), use_frontcode=True
    )
    assert frontcoded_path.stat().st_size < legacy_path.stat().st_size
