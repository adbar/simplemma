"""Front-coded byte-stream decoder for `dict[bytes, bytes]` dictionaries.

Keys are sorted and front-coded (each stores only the bytes not shared with the
previous key's prefix); values are suffix-edited against their own key. The flat
stream compresses far better under lzma than a pickled dict.

`_decode_stream` is the runtime path. The build-time encoder lives in
``training/frontcode_encode.py``.

`_read_header`/`_iter_records` expose the format at record granularity for
partial/resumable reads.
"""

from collections.abc import Iterator

_MAGIC = b"SMFC1"
_REVERSE_FLAG = 0x01

# Trim-byte sentinels (a real trim is small, so 254/255 are free).
_SAME_AS_PREV = 254
_LITERAL_VALUE = 255

# Shared by _decode_stream and StreamMap; tests match on it too.
_CORRUPT_STREAM_MSG = "truncated or corrupt front-coded stream"


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


def _is_frontcoded(data: bytes) -> bool:
    """True if the (decompressed) `data` starts with the format magic."""
    return data[: len(_MAGIC)] == _MAGIC


def _read_header(data: bytes) -> tuple[bool, int, int]:
    """Parse the magic/flag/count header. Returns (reverse_key, count, pos)
    where pos is the byte offset of the first record."""
    if not _is_frontcoded(data):
        raise ValueError("not a front-coded stream")
    pos = len(_MAGIC)
    reverse_key = bool(data[pos] & _REVERSE_FLAG)
    pos += 1
    count, pos = _read_varint(data, pos)
    return reverse_key, count, pos


def _iter_records(
    data: bytes, pos: int, prev_key: bytes = b"", prev_value: bytes = b""
) -> Iterator[tuple[int, bytes, bytes]]:
    """Yield (record_start, stored_key, stored_value) from `pos` to the end of
    `data`, resuming front-code decoding from the given seed. Keys/values are
    in on-disk form: sorted, not un-reversed for `reverse_key` streams.

    The single per-record decoder used by both `_decode_stream` and `StreamMap`.
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


def _decode_stream(data: bytes) -> dict[bytes, bytes]:
    """Decode already-decompressed front-coded bytes.

    Assumes a well-formed `_encode` stream; truncation or trailing garbage
    raises ValueError."""
    reverse_key, count, pos = _read_header(data)

    result: dict[bytes, bytes] = {}
    n = 0
    for _, stored_key, stored_value in _iter_records(data, pos):
        key = stored_key[::-1] if reverse_key else stored_key
        value = stored_value[::-1] if reverse_key else stored_value
        result[key] = value
        n += 1

    # a truncated stream ending on a boundary yields too few records
    if n != count:
        raise ValueError(_CORRUPT_STREAM_MSG)
    return result
