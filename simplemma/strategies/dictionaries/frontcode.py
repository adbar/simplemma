"""Front-coded byte-stream codec for `dict[bytes, bytes]` dictionaries.

Keys are sorted and front-coded (each stores only the bytes not shared with the
previous key's prefix); values are suffix-edited against their own key. The flat
stream compresses far better under lzma than a pickled dict. `decode_stream` is
the runtime path; `encode` runs at build time (training/dictionary_builder.py).

`read_header`/`iter_records` expose the format at record granularity for
partial/resumable reads.
"""

import lzma
from collections.abc import Iterator

MAGIC = b"SMFC1"
_REVERSE_FLAG = 0x01

# Trim-byte sentinels (a real trim is small, so 254/255 are free).
_SAME_AS_PREV = 254
_LITERAL_VALUE = 255

# Shared by decode_stream and StreamMap; tests match on it too.
_CORRUPT_STREAM_MSG = "truncated or corrupt front-coded stream"


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
    """True if the (decompressed) `data` starts with the format magic."""
    return data[: len(MAGIC)] == MAGIC


def encode(mapping: dict[bytes, bytes], reverse_key: bool = False) -> bytes:
    """Encode a bytes->bytes dict into a front-coded, lzma-compressed blob.

    reverse_key front-codes reversed bytes, for prefixing morphology (e.g.
    Swahili, where forms share a suffix not a prefix).
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


def read_header(data: bytes) -> tuple[bool, int, int]:
    """Parse the magic/flag/count header. Returns (reverse_key, count, pos)
    where pos is the byte offset of the first record."""
    if not is_frontcoded(data):
        raise ValueError("not a front-coded stream")
    pos = len(MAGIC)
    reverse_key = bool(data[pos] & _REVERSE_FLAG)
    pos += 1
    count, pos = _read_varint(data, pos)
    return reverse_key, count, pos


def iter_records(
    data: bytes, pos: int, prev_key: bytes = b"", prev_value: bytes = b""
) -> Iterator[tuple[int, bytes, bytes]]:
    """Yield (record_start, stored_key, stored_value) from `pos` to the end of
    `data`, resuming front-code decoding from the given seed. Keys/values are
    in on-disk form: sorted, not un-reversed for `reverse_key` streams.

    The single per-record decoder used by both `decode_stream` and `StreamMap`.
    Almost-always-single-byte varints are read inline; rare multi-byte ones
    fall back to `_read_varint` (measured 1.5-1.6x on shipped dicts). Raises
    ValueError on a slice/varint that runs past the buffer.
    """
    n = len(data)
    try:
        while pos < n:
            record_start = pos
            byte = data[pos]
            if byte < 0x80:
                shared, pos = byte, pos + 1
            else:
                shared, pos = _read_varint(data, pos)
            byte = data[pos]
            if byte < 0x80:
                suflen, pos = byte, pos + 1
            else:
                suflen, pos = _read_varint(data, pos)
            end = pos + suflen
            if end > n:
                raise ValueError(_CORRUPT_STREAM_MSG)
            stored_key = prev_key[:shared] + data[pos:end]
            pos = end

            trim = data[pos]
            pos += 1
            if trim == _SAME_AS_PREV:
                stored_value = prev_value
            else:
                byte = data[pos]
                if byte < 0x80:
                    vlen, pos = byte, pos + 1
                else:
                    vlen, pos = _read_varint(data, pos)
                end = pos + vlen
                if end > n:
                    raise ValueError(_CORRUPT_STREAM_MSG)
                if trim == _LITERAL_VALUE:
                    stored_value = data[pos:end]
                else:
                    stored_value = stored_key[: len(stored_key) - trim] + data[pos:end]
                pos = end

            yield record_start, stored_key, stored_value
            prev_key, prev_value = stored_key, stored_value
    except IndexError:
        # a truncated varint/trim byte overruns the buffer
        raise ValueError(_CORRUPT_STREAM_MSG) from None


def decode_stream(data: bytes) -> dict[bytes, bytes]:
    """Decode already-decompressed front-coded bytes.

    Assumes a well-formed `encode` stream; truncation or trailing garbage
    raises ValueError."""
    reverse_key, count, pos = read_header(data)

    result: dict[bytes, bytes] = {}
    n = 0
    for _, stored_key, stored_value in iter_records(data, pos):
        key = stored_key[::-1] if reverse_key else stored_key
        value = stored_value[::-1] if reverse_key else stored_value
        result[key] = value
        n += 1

    # a truncated stream ending on a boundary yields too few records
    if n != count:
        raise ValueError(_CORRUPT_STREAM_MSG)
    return result


def decode(blob: bytes) -> dict[bytes, bytes]:
    """Decompress and decode a full blob (inverse of `encode`)."""
    return decode_stream(lzma.decompress(blob))
