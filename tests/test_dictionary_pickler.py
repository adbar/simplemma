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
    # dict generation
    testfile = str(TEST_DIR / "data/zz.txt")
    # simple generation, silent mode
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=True)
    assert len(mydict) == 3
    mydict = dictionary_pickler._load_dict(
        "zz", listpath=str(TEST_DIR / "data"), silent=True
    )
    assert len(mydict) == 3
    # log warning (silent=False branch)
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=False)
    assert len(mydict) == 3

    # file I/O
    assert dictionary_pickler._determine_path("lists", "de").endswith("de.txt")

    # dict pickling — round-trip
    listpath = str(TEST_DIR / "data")
    temp_outputfile = str(tmp_path / "zz.pkl")
    dictionary_pickler._pickle_dict("zz", listpath, temp_outputfile)
    with lzma.open(temp_outputfile, "rb") as f:
        roundtripped = pickle.load(f)
    assert isinstance(roundtripped, dict)
    assert len(roundtripped) == 3
    assert all(isinstance(k, bytes) for k in roundtripped)

    dictionary_pickler._pickle_dict("zz", listpath, in_place=True)

    # remove pickle file (in_place=True writes into the real package data dir)
    filepath = dictionary_pickler._determine_pickle_path("zz", in_place=True)
    Path(filepath).unlink(missing_ok=True)


def test_read_dict_filtering(tmp_path) -> None:
    """Valid pair + identity, punctuation drop, length-difference drop, conflict."""
    result = _read(
        tmp_path,
        "en",
        "dog\tdogs\n"  # valid: word -> lemma, plus lemma identity
        "foo,bar\tbaz\n"  # punctuation -> dropped
        "a\tverylongword\n"  # lemma length 1 & word > 6 -> dropped
        "verylonglemma\tx\n"  # lemma > 6 & word length 1 -> dropped
        "run\trunning\n"  # sets running -> run
        "xunning\trunning\n",  # conflict: closer lemma wins
    )
    assert result == {
        b"dog": b"dog",
        b"dogs": b"dog",
        b"run": b"run",
        b"running": b"xunning",
    }


def test_read_dict_voc_limit(tmp_path) -> None:
    """VOC_LIMIT language drops entries longer than MAXLENGTH (16)."""
    result = _read(
        tmp_path,
        "fi",
        "talo\ttalot\n"  # within limit -> kept
        "short\tthiswordislongerthan16\n",  # word > 16 chars -> dropped
    )
    assert result == {b"talo": b"talo", b"talot": b"talo"}


def test_read_dict_buffer_hack(tmp_path) -> None:
    """BUFFER_HACK forces a lemma identity, overwriting a prior mapping."""
    # "de" is not in BUFFER_HACK: the prior bb -> xx mapping stands.
    non_hack = _read(tmp_path, "de", "xx\tbb\nbb\tyy\n")
    assert non_hack[b"bb"] == b"xx"
    # "et" is in BUFFER_HACK: bb is overwritten to its own identity.
    hack = _read(tmp_path, "et", "xx\tbb\nbb\tyy\n")
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
    assert lemmatizer.lemmatize("dogs", lang="zz") == "dog"  # inflected -> lemma
    assert lemmatizer.lemmatize("xyz", lang="zz") == "xyz"  # OOV passthrough


def test_generated_plzma_loads_through_real_reader(tmp_path, monkeypatch) -> None:
    """Pre-flight for live generation: a pickled .plzma loads via the production
    reader and lemmatizes — proving the pickler-output/factory-reader contract."""
    (tmp_path / "zz.txt").write_text("dog\tdogs\ncat\tcats\n", encoding="utf-8")
    dictionary_pickler._pickle_dict(
        "zz", listpath=str(tmp_path), filepath=str(tmp_path / "zz.plzma")
    )

    # Load exactly as DefaultDictionaryFactory does, pointed at the fresh file.
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    raw = dictionary_factory._load_dictionary_from_disk("zz")

    class GeneratedFactory(DictionaryFactory):
        def get_dictionary(self, lang: str) -> MappingStrToByteString:
            return MappingStrToByteString(raw)

    lemmatizer = Lemmatizer(
        lemmatization_strategy=DefaultStrategy(dictionary_factory=GeneratedFactory())
    )
    assert lemmatizer.lemmatize("dogs", lang="zz") == "dog"
