import lzma
from functools import lru_cache

import pytest

from simplemma.strategies import DefaultDictionaryFactory, StreamDictionaryFactory
from simplemma.strategies.dictionaries import dictionary_factory, frontcode
from training.frontcode_encode import _encode as _fc_encode
from simplemma.strategies.dictionaries.stream_dictionary_factory import (
    _BLOCK_SIZE,
    StreamMap,
)

# sw is reverse-coded (prefixal morphology); de/en are not.
LANGS = ["de", "en", "sw"]

# Cache per lang: both builders are O(n) full-stream passes.
_reference = lru_cache(maxsize=None)(
    lambda lang: dict(DefaultDictionaryFactory().get_dictionary(lang))
)
_stream = lru_cache(maxsize=None)(StreamMap)


def _streammap_from_bytes(
    blob: bytes, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> StreamMap:
    """Write a synthetic `.plzma` into a temp DATA_FOLDER and build its StreamMap."""
    (tmp_path / "tst.plzma").write_bytes(blob)
    monkeypatch.setattr(dictionary_factory, "DATA_FOLDER", tmp_path)
    monkeypatch.setattr(dictionary_factory, "SUPPORTED_LANGUAGES", frozenset({"tst"}))
    return StreamMap("tst")


def test_exceptions() -> None:
    dictionary_factory = StreamDictionaryFactory()
    with pytest.raises(ValueError, match="Unsupported language"):
        dictionary_factory.get_dictionary("abc")


@pytest.mark.parametrize("lang", ["../secrets", "/etc/passwd", "sub/de", "", "xyz"])
def test_streammap_rejects_bad_language_codes(lang: str) -> None:
    with pytest.raises(ValueError, match="Unsupported language"):
        StreamMap(lang)


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
    """Stride-sampled; a full sw sweep is too slow for routine runs."""
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
    reference = _reference(lang)
    stream = _stream(lang)

    assert len(stream) == len(reference)
    assert set(stream) == set(reference)


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
    stream = _streammap_from_bytes(
        _fc_encode(reference, reverse), tmp_path, monkeypatch
    )

    decoded = {k.decode(): v.decode() for k, v in reference.items()}
    assert len(stream) == count
    assert set(stream) == set(decoded)
    for key, value in decoded.items():
        assert stream.get(key) == value
    assert stream.get("aaaaaa") is None
    assert stream.get("zzzzzz") is None
    assert stream.get("word000000extra") is None


def test_truncated_stream_raises(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    reference = {
        f"word{i:04d}".encode(): f"lemma{i:04d}".encode()
        for i in range(2 * _BLOCK_SIZE)
    }
    raw = lzma.decompress(_fc_encode(reference))
    _, _, pos = frontcode._read_header(raw)
    starts = [start for start, _, _ in frontcode._iter_records(raw, pos)]
    truncated = raw[: starts[_BLOCK_SIZE]]

    with pytest.raises(ValueError, match="truncated or corrupt"):
        _streammap_from_bytes(lzma.compress(truncated), tmp_path, monkeypatch)


def test_trailing_garbage_raises(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    reference = {b"word0000": b"lemma0000", b"word0001": b"lemma0001"}
    raw = lzma.decompress(_fc_encode(reference))
    extra_record = bytes([0, 4]) + b"zzzz" + bytes([254])
    padded = raw + extra_record

    with pytest.raises(ValueError, match="truncated or corrupt"):
        _streammap_from_bytes(lzma.compress(padded), tmp_path, monkeypatch)


def test_synthetic_literal_value(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # forces the rare _LITERAL_VALUE branch (no shipped key is this long)
    key = "a" * 300
    reference = {key.encode(): b"lemma"}
    stream = _streammap_from_bytes(_fc_encode(reference), tmp_path, monkeypatch)

    assert len(stream) == 1
    assert list(stream) == [key]
    assert stream.get(key) == "lemma"
