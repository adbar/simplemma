"""Memory-frugal `DictionaryFactory` that reads `.plzma` front-coded streams
directly instead of building a full `dict[bytes, bytes]` in RAM.

Front-coding is sequential, so random access needs restart points: one pass
builds a sparse per-block seed index, then each lookup bisects to a block and
decodes only its few records. Trades RAM for lookup speed; see README.
"""

from bisect import bisect_right
from collections.abc import Iterator, Mapping

from . import frontcode
from .dictionary_factory import (
    CachingDictionaryFactory,
    DecodedStrMapping,
    _read_decompressed,
)

_BLOCK_SIZE = 32


class StreamMap(DecodedStrMapping):
    """Read-only str->str view over a front-coded stream, decoded on demand.

    `_firsts` holds each block's first key (for bisect); `_blocks` its
    (offset, prev_key, prev_value) resume seed.
    """

    __slots__ = ("_data", "_pos", "_rev", "_count", "_firsts", "_blocks")

    def __init__(self, lang: str) -> None:
        self._data = _read_decompressed(lang)
        self._rev, self._count, self._pos = frontcode._read_header(self._data)

        firsts: list[bytes] = []
        blocks: list[tuple[int, bytes, bytes]] = []
        prev_key, prev_value = b"", b""
        index = -1
        for index, (record_start, stored_key, stored_value) in enumerate(
            frontcode._iter_records(self._data, self._pos)
        ):
            if index % _BLOCK_SIZE == 0:
                firsts.append(stored_key)
                blocks.append((record_start, prev_key, prev_value))
            prev_key, prev_value = stored_key, stored_value
        # catches a stream ending on a boundary with the wrong record count
        if index + 1 != self._count:
            raise ValueError(frontcode._CORRUPT_STREAM_MSG)
        self._firsts = firsts
        self._blocks = blocks

    def _lookup(self, key: str) -> str | None:
        target = key.encode()
        if self._rev:
            target = target[::-1]

        block = bisect_right(self._firsts, target) - 1
        if block < 0:
            return None

        # sorted keys bound the scan: the next block's first key exceeds target
        for _, stored_key, stored_value in frontcode._iter_records(
            self._data, *self._blocks[block]
        ):
            if stored_key == target:
                value = stored_value[::-1] if self._rev else stored_value
                return value.decode()
            if stored_key > target:
                return None
        return None

    def __iter__(self) -> Iterator[str]:
        for _, stored_key, _ in frontcode._iter_records(self._data, self._pos):
            key = stored_key[::-1] if self._rev else stored_key
            yield key.decode()

    def __len__(self) -> int:
        return self._count


class StreamDictionaryFactory(CachingDictionaryFactory):
    """`DictionaryFactory` backed by direct front-coded stream reads."""

    __slots__ = ()

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        return StreamMap(lang)
