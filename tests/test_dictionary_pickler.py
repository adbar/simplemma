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
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=True)
    assert len(mydict) == 4
    mydict = dictionary_pickler._load_dict(
        "zz", listpath=str(TEST_DIR / "data"), silent=True
    )
    assert len(mydict) == 4
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=False)
    assert len(mydict) == 4

    assert dictionary_pickler._determine_path("lists", "de").endswith("de.txt")

    listpath = str(TEST_DIR / "data")
    temp_outputfile = str(tmp_path / "zz.pkl")
    dictionary_pickler._pickle_dict("zz", listpath, temp_outputfile)
    with lzma.open(temp_outputfile, "rb") as f:
        roundtripped = pickle.load(f)
    assert isinstance(roundtripped, dict)
    assert len(roundtripped) == 4
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


def test_read_dict_voc_limit(tmp_path) -> None:
    """VOC_LIMIT language drops entries longer than MAXLENGTH (16)."""
    result = _read(
        tmp_path,
        "fi",
        "talo\ttalot\nshort\tthiswordislongerthan16\n",
    )
    assert result == {b"talo": b"talo", b"talot": b"talo"}


def test_read_dict_buffer_hack(tmp_path) -> None:
    """BUFFER_HACK forces a lemma identity, overwriting a prior mapping."""
    non_hack = _read(tmp_path, "de", "xx\tbb\nbb\tyy\n")  # de not in BUFFER_HACK
    assert non_hack[b"bb"] == b"xx"
    hack = _read(tmp_path, "et", "xx\tbb\nbb\tyy\n")  # et is in BUFFER_HACK
    assert hack[b"bb"] == b"bb"


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
