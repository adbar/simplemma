"""Build-time encoder for the front-coded dictionary format.

The decoder lives in simplemma.strategies.dictionaries.frontcode (runtime).
"""

import lzma

from simplemma.strategies.dictionaries.frontcode import (
    _LITERAL_VALUE,
    _MAGIC,
    _REVERSE_FLAG,
    _SAME_AS_PREV,
    _decode_stream,
)


def _write_varint(buf: bytearray, value: int) -> None:
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            buf.append(byte | 0x80)
        else:
            buf.append(byte)
            return


def _common_prefix_len(a: bytes, b: bytes) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _encode(mapping: dict[bytes, bytes], reverse_key: bool = False) -> bytes:
    """Encode a bytes->bytes dict into a front-coded, lzma-compressed blob.

    reverse_key front-codes reversed bytes, for prefixing morphology (e.g.
    Swahili, where forms share a suffix not a prefix).
    """
    items = sorted(
        mapping.items(), key=lambda kv: kv[0][::-1] if reverse_key else kv[0]
    )

    stream = bytearray(_MAGIC)
    stream.append(_REVERSE_FLAG if reverse_key else 0)
    _write_varint(stream, len(items))

    prev_key = b""
    prev_value: bytes | None = None
    for key, value in items:
        stored_key = key[::-1] if reverse_key else key
        stored_value = value[::-1] if reverse_key else value

        shared = _common_prefix_len(prev_key, stored_key)
        suffix = stored_key[shared:]
        _write_varint(stream, shared)
        _write_varint(stream, len(suffix))
        stream += suffix

        if stored_value == prev_value:
            stream.append(_SAME_AS_PREV)
        else:
            prefix_len = _common_prefix_len(stored_key, stored_value)
            trim = len(stored_key) - prefix_len
            value_suffix = stored_value[prefix_len:]
            if trim >= _SAME_AS_PREV:
                # trim too big for one byte: store the value whole.
                stream.append(_LITERAL_VALUE)
                _write_varint(stream, len(stored_value))
                stream += stored_value
            else:
                stream.append(trim)
                _write_varint(stream, len(value_suffix))
                stream += value_suffix

        prev_key = stored_key
        prev_value = stored_value

    return lzma.compress(bytes(stream), preset=9 | lzma.PRESET_EXTREME)


def _decode(blob: bytes) -> dict[bytes, bytes]:
    """Decompress and decode a full blob (inverse of `_encode`)."""
    return _decode_stream(lzma.decompress(blob))
