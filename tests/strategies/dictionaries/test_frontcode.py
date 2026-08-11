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
        # adjacent keys sharing the exact same value hit the same-as-prev sentinel
        pytest.param(
            {b"aa": b"x", b"ab": b"x", b"ac": b"x", b"bb": b"y"},
            False,
            id="repeated-values-run-encoding",
        ),
        # reverse_key=True front-codes shared suffixes (prefixal morphology)
        pytest.param(
            {b"nakisoma": b"soma", b"anasoma": b"soma", b"atasoma": b"soma"},
            True,
            id="reverse-key",
        ),
        # a value sharing nothing with a long key forces the literal-value path
        pytest.param({b"x" * 300: b"y" * 300}, False, id="literal-value-fallback"),
        # a >=128-byte shared prefix forces the multi-byte varint path for
        # `shared` (real dicts never trigger this; _decode_stream's fast path
        # for single-byte varints has a separate fallback branch to cover)
        pytest.param(
            {b"a" * 200 + b"aa": b"x", b"a" * 200 + b"bb": b"y"},
            False,
            id="long-shared-prefix",
        ),
        # trim=0 must not corrupt the value (see the `token[:-0]` gotcha)
        pytest.param(
            {b"run": b"run", b"running": b"runningly"},
            False,
            id="trim-zero-self-identity",
        ),
    ],
)
def test_roundtrip(mapping: dict[bytes, bytes], reverse_key: bool) -> None:
    assert _fc_decode(_fc_encode(mapping, reverse_key)) == mapping


def test_is_frontcoded_rejects_other_data() -> None:
    assert frontcode._is_frontcoded(b"not a front-coded stream") is False


def test_decode_stream_rejects_non_frontcoded_data() -> None:
    with pytest.raises(ValueError, match="not a front-coded stream"):
        frontcode._decode_stream(b"\x80\x05some pickle bytes")


def test_decode_stream_rejects_truncated_trailing_suffix() -> None:
    """Truncation inside a trailing value-suffix overruns a slice silently; the
    length check must reject it instead of returning a corrupt short value."""
    raw = lzma.decompress(_fc_encode({b"dog": b"dog", b"zz": b"zzabc"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw[:-1])


def test_decode_stream_rejects_truncated_key_suffix() -> None:
    """Truncation inside a key-suffix (as opposed to a value-suffix) must also
    raise, not just return a shortened key."""
    raw = lzma.decompress(_fc_encode({b"dog": b"dog", b"zzzzzz": b"zzzzzz"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw[:-6])


def test_decode_stream_rejects_trailing_garbage() -> None:
    raw = lzma.decompress(_fc_encode({b"dog": b"dog"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw + b"\x00")


def test_decode_stream_rejects_boundary_truncated_records() -> None:
    """Dropping a whole trailing record leaves no partial garbage, so only the
    record-count check (not _iter_records' bounds check) can catch it."""
    mapping = {b"ant": b"ant", b"bee": b"bee", b"cat": b"cat"}
    raw = lzma.decompress(_fc_encode(mapping))
    _, _, pos = frontcode._read_header(raw)
    starts = [start for start, _, _ in frontcode._iter_records(raw, pos)]
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode._decode_stream(raw[: starts[-1]])
