import lzma

import pytest

from simplemma.strategies.dictionaries import frontcode
from training.frontcode_encode import _decode as _fc_decode, _encode as _fc_encode


@pytest.mark.parametrize(
    ("mapping", "reverse_key"),
    [
        pytest.param(
            {b"dog": b"dog", b"dogs": b"dog", b"cat": b"cat", b"running": b"run"},
            False,
            id="basic",
        ),
        pytest.param({}, False, id="empty"),
        pytest.param(
            {b"aa": b"x", b"ab": b"x", b"ac": b"x", b"bb": b"y"},
            False,
            id="repeated-values-run-encoding",
        ),
        pytest.param(
            {b"nakisoma": b"soma", b"anasoma": b"soma", b"atasoma": b"soma"},
            True,
            id="reverse-key",
        ),
        pytest.param({b"x" * 300: b"y" * 300}, False, id="literal-value-fallback"),
        # a shared prefix of 128 bytes or more needs a multi-byte varint
        pytest.param(
            {b"a" * 200 + b"aa": b"x", b"a" * 200 + b"bb": b"y"},
            False,
            id="long-shared-prefix",
        ),
        # trim=0 must not hit the `token[:-0]` gotcha
        pytest.param(
            {b"run": b"run", b"running": b"runningly"},
            False,
            id="trim-zero-self-identity",
        ),
    ],
)
def test_roundtrip(mapping: dict[bytes, bytes], reverse_key: bool) -> None:
    assert _fc_decode(_fc_encode(mapping, reverse_key)) == mapping


def test_decode_stream_rejects_non_frontcoded_data() -> None:
    with pytest.raises(ValueError, match="not a front-coded stream"):
        frontcode._decode_stream(b"\x80\x05some pickle bytes")


def test_decode_stream_rejects_truncated_trailing_suffix() -> None:
    """Truncation inside a value suffix would otherwise pass a silent slice."""
    raw = lzma.decompress(_fc_encode({b"dog": b"dog", b"zz": b"zzabc"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw[:-1])


def test_decode_stream_rejects_truncated_key_suffix() -> None:
    raw = lzma.decompress(_fc_encode({b"dog": b"dog", b"zzzzzz": b"zzzzzz"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw[:-6])


def test_decode_stream_rejects_trailing_garbage() -> None:
    raw = lzma.decompress(_fc_encode({b"dog": b"dog"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw + b"\x00")


def test_decode_stream_rejects_boundary_truncated_records() -> None:
    """Only the record-count check can catch a dropped whole trailing record."""
    mapping = {b"ant": b"ant", b"bee": b"bee", b"cat": b"cat"}
    raw = lzma.decompress(_fc_encode(mapping))
    _, _, pos = frontcode._read_header(raw)
    starts = [start for start, _, _ in frontcode._iter_records(raw, pos)]
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw[: starts[-1]])
