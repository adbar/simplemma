"""
Front-coded byte-stream codec for `dict[bytes, bytes]` dictionaries.

Keys are sorted and front-coded (each key stores only the bytes it doesn't
share with the previous key's prefix); values are suffix-edited relative to
their own key (most lemmas differ from their form by only a short suffix).
The resulting flat stream compresses far better under lzma than a pickled
dict, because adjacent inflected forms end up byte-adjacent instead of
scattered by pickle's own ordering.

Decoding lives here (runtime dependency); encoding is called from
`training/dictionary_pickler.py` (build-time only).
"""

import lzma

MAGIC = b"SMFC1"
_REVERSE_FLAG = 0x01

# Trim-byte sentinels: a real trim is small, so 254/255 are free.
_SAME_AS_PREV = 254
_LITERAL_VALUE = 255


def _write_varint(buf: bytearray, value: int) -> None:
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            buf.append(byte | 0x80)
        else:
            buf.append(byte)
            return


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def _common_prefix_len(a: bytes, b: bytes) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def is_frontcoded(data: bytes) -> bool:
    """Peek at already-decompressed bytes to distinguish this format from a legacy pickle."""
    return data[: len(MAGIC)] == MAGIC


def encode(mapping: dict[bytes, bytes], reverse_key: bool = False) -> bytes:
    """Encode a bytes->bytes dict into a front-coded, lzma-compressed blob.

    reverse_key: front-code the reversed bytes instead (helps prefixing
    morphology, e.g. Swahili, where forms share a suffix, not a prefix).
    """
    items = sorted(
        mapping.items(), key=lambda kv: kv[0][::-1] if reverse_key else kv[0]
    )

    stream = bytearray(MAGIC)
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


def decode_stream(data: bytes) -> dict[bytes, bytes]:
    """Decode already-decompressed front-coded bytes (see `is_frontcoded`).

    Assumes a well-formed stream as produced by `encode`; a truncated or
    corrupt stream raises IndexError rather than a specific decode error."""
    if not is_frontcoded(data):
        raise ValueError("not a front-coded stream")
    pos = len(MAGIC)
    reverse_key = bool(data[pos] & _REVERSE_FLAG)
    pos += 1
    count, pos = _read_varint(data, pos)

    result: dict[bytes, bytes] = {}
    prev_key = b""
    prev_value = b""
    for _ in range(count):
        shared, pos = _read_varint(data, pos)
        suflen, pos = _read_varint(data, pos)
        suffix = data[pos : pos + suflen]
        pos += suflen
        stored_key = prev_key[:shared] + suffix

        trim = data[pos]
        pos += 1
        if trim == _SAME_AS_PREV:
            stored_value = prev_value
        elif trim == _LITERAL_VALUE:
            vlen, pos = _read_varint(data, pos)
            stored_value = data[pos : pos + vlen]
            pos += vlen
        else:
            vlen, pos = _read_varint(data, pos)
            value_suffix = data[pos : pos + vlen]
            pos += vlen
            stored_value = stored_key[: len(stored_key) - trim] + value_suffix

        key = stored_key[::-1] if reverse_key else stored_key
        value = stored_value[::-1] if reverse_key else stored_value
        result[key] = value

        prev_key = stored_key
        prev_value = stored_value

    return result


def decode(blob: bytes) -> dict[bytes, bytes]:
    """Decompress and decode a full front-coded blob (as produced by `encode`)."""
    return decode_stream(lzma.decompress(blob))
