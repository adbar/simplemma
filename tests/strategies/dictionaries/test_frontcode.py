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
        b"nakisoma": b"soma",  # subject+TAM markers prepended, stem shared at the end
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


def test_roundtrip_trim_zero_self_identity() -> None:
    """trim=0 (self-identity/near-identity) must not corrupt the value (see the
    documented `token[:-0]` gotcha for suffix-edit encodings)."""
    mapping = {b"run": b"run", b"running": b"runningly"}
    assert frontcode.decode(frontcode.encode(mapping)) == mapping


def test_is_frontcoded_rejects_other_data() -> None:
    assert frontcode.is_frontcoded(b"not a front-coded stream") is False


def test_decode_stream_rejects_non_frontcoded_data() -> None:
    with pytest.raises(ValueError, match="not a front-coded stream"):
        frontcode.decode_stream(b"\x80\x05some pickle bytes")
