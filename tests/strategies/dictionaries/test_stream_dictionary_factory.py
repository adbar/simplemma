from functools import lru_cache

import pytest

from simplemma.strategies import DefaultDictionaryFactory, StreamDictionaryFactory
from simplemma.strategies.dictionaries import dictionary_factory, frontcode
from simplemma.strategies.dictionaries.stream_dictionary_factory import (
    _BLOCK_SIZE,
    StreamMap,
)

# de/en: normal (non-reversed) streams. sw: reverse-coded (suffix morphology).
LANGS = ["de", "en", "sw"]

# Both builders are O(n) full-stream passes; cache per lang so the LANGS-
# parametrized tests below don't redecode sw's ~4.9M entries repeatedly.
_reference = lru_cache(maxsize=None)(
    lambda lang: dict(DefaultDictionaryFactory().get_dictionary(lang))
)
_stream = lru_cache(maxsize=None)(StreamMap)


def test_exceptions() -> None:
    dictionary_factory = StreamDictionaryFactory()
    with pytest.raises(ValueError, match="Unsupported language"):
        dictionary_factory.get_dictionary("abc")


def test_dictionary_lru_cache() -> None:
    iterations = 10
    dictionaries = StreamDictionaryFactory()
    for _ in range(iterations):
        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("de")
    assert dictionaries._get_dictionary.cache_info().misses == 2
    assert dictionaries._get_dictionary.cache_info().hits == (iterations - 1) * 2
    assert dictionaries.get_dictionary("en") is dictionaries.get_dictionary("en")


_SAMPLE_SIZE = 3000


@pytest.mark.parametrize("lang", LANGS)
def test_get_parity_sampled_sweep(lang: str) -> None:
    """Stride-sampled over the whole sorted key range; a full sweep of sw's
    ~4.9M entries is too slow for routine runs (see the en full-sweep test)."""
    reference = _reference(lang)
    stream = _stream(lang)

    assert len(stream) == len(reference)
    keys = sorted(reference)
    stride = max(1, len(keys) // _SAMPLE_SIZE)
    for key in keys[::stride]:
        value = reference[key]
        assert stream.get(key) == value
        assert stream[key] == value
        assert key in stream
    # first/last keys exercise the first and last seed blocks
    for key in (keys[0], keys[-1]):
        assert stream.get(key) == reference[key]


def test_get_parity_full_sweep_small_lang() -> None:
    lang = "en"
    reference = _reference(lang)
    stream = _stream(lang)

    for key, value in reference.items():
        assert stream.get(key) == value


@pytest.mark.parametrize("lang", LANGS)
def test_misses(lang: str) -> None:
    reference = _reference(lang)
    stream = _stream(lang)

    assert stream.get("\x00\x00\x00") is None  # sorts before the first block
    assert stream.get("￿￿￿") is None  # sorts past the last block
    absent = "zzzzzqqqqqxxxxx"
    assert absent not in reference
    assert stream.get(absent) is None
    assert stream.get(absent, "fallback") == "fallback"
    with pytest.raises(KeyError):
        _ = stream[absent]
    assert (absent in stream) is False


@pytest.mark.parametrize("lang", LANGS)
def test_iter_and_len_parity(lang: str) -> None:
    """Key-set parity via the cheap `__iter__` walk (values covered by the get
    sweeps). Avoids `dict(stream)`, which re-decodes per-key via `__getitem__`."""
    reference = _reference(lang)
    stream = _stream(lang)

    assert len(stream) == len(reference)
    assert sorted(stream) == sorted(reference)


# Only synthetic streams reach count == 0 and the sub-block / first-block edges
# of the bisect math (the smallest shipped dict has hundreds of blocks).
@pytest.mark.parametrize(
    "count", [0, 1, 2, _BLOCK_SIZE - 1, _BLOCK_SIZE, _BLOCK_SIZE + 1, 2 * _BLOCK_SIZE]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_synthetic_block_boundaries(
    count: int, reverse: bool, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference = {
        f"word{i:06d}".encode(): f"lemma{i:06d}".encode() for i in range(count)
    }
    (tmp_path / "tst.plzma").write_bytes(frontcode.encode(reference, reverse))
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    stream = StreamMap("tst")

    decoded = {k.decode(): v.decode() for k, v in reference.items()}
    assert len(stream) == count
    assert set(stream) == set(decoded)
    for key, value in decoded.items():
        assert stream.get(key) == value
    # misses below, above, and inside the key range
    assert stream.get("aaaaaa") is None
    assert stream.get("zzzzzz") is None
    assert stream.get("word000000extra") is None


def test_synthetic_literal_value(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A key too long for its value to be suffix-coded forces the rare
    # _LITERAL_VALUE branch (shipped dicts have no keys this long).
    key = "a" * 300
    reference = {key.encode(): b"lemma"}
    (tmp_path / "tst.plzma").write_bytes(frontcode.encode(reference))
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    stream = StreamMap("tst")

    assert len(stream) == 1
    assert list(stream) == [key]
    assert stream.get(key) == "lemma"
