import lzma

import pytest

from simplemma.strategies.dictionaries import frontcode


def test_roundtrip_basic() -> None:
    mapping = {
        b"dog": b"dog",
        b"dogs": b"dog",
        b"cat": b"cat",
        b"cats": b"cat",
        b"running": b"run",
    }
    assert frontcode.decode(frontcode.encode(mapping)) == mapping


def test_roundtrip_empty() -> None:
    assert frontcode.decode(frontcode.encode({})) == {}


def test_roundtrip_repeated_values_run_encoding() -> None:
    """Adjacent keys sharing the exact same value hit the same-as-prev sentinel."""
    mapping = {b"aa": b"x", b"ab": b"x", b"ac": b"x", b"bb": b"y"}
    assert frontcode.decode(frontcode.encode(mapping)) == mapping


def test_roundtrip_reverse_key() -> None:
    """reverse_key=True front-codes shared suffixes (prefixal morphology)."""
    mapping = {
        b"nakisoma": b"soma",  # stem shared at the end
        b"anasoma": b"soma",
        b"atasoma": b"soma",
    }
    assert frontcode.decode(frontcode.encode(mapping, reverse_key=True)) == mapping


def test_roundtrip_literal_value_fallback() -> None:
    """A value sharing (almost) nothing with a long key forces the literal-value path."""
    long_key = b"x" * 300
    unrelated_value = b"y" * 300
    mapping = {long_key: unrelated_value}
    assert frontcode.decode(frontcode.encode(mapping)) == mapping


def test_roundtrip_long_shared_prefix() -> None:
    """Two keys sharing a >=128-byte prefix force the multi-byte varint path
    for `shared` (real dicts never trigger this; decode_stream's fast path
    for single-byte varints has a separate fallback branch to cover)."""
    mapping = {b"a" * 200 + b"aa": b"x", b"a" * 200 + b"bb": b"y"}
    assert frontcode.decode(frontcode.encode(mapping)) == mapping


def test_roundtrip_trim_zero_self_identity() -> None:
    """trim=0 must not corrupt the value (see the `token[:-0]` gotcha)."""
    mapping = {b"run": b"run", b"running": b"runningly"}
    assert frontcode.decode(frontcode.encode(mapping)) == mapping


def test_is_frontcoded_rejects_other_data() -> None:
    assert frontcode.is_frontcoded(b"not a front-coded stream") is False


def test_decode_stream_rejects_non_frontcoded_data() -> None:
    with pytest.raises(ValueError, match="not a front-coded stream"):
        frontcode.decode_stream(b"\x80\x05some pickle bytes")


def test_decode_stream_rejects_truncated_trailing_suffix() -> None:
    """Truncation inside a trailing value-suffix overruns a slice silently; the
    length check must reject it instead of returning a corrupt short value."""
    raw = lzma.decompress(frontcode.encode({b"dog": b"dog", b"zz": b"zzabc"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode.decode_stream(raw[:-1])


def test_decode_stream_rejects_trailing_garbage() -> None:
    raw = lzma.decompress(frontcode.encode({b"dog": b"dog"}))
    with pytest.raises(ValueError, match="truncated or corrupt"):
        frontcode.decode_stream(raw + b"\x00")
