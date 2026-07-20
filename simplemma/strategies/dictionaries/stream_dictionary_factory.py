"""Memory-frugal `DictionaryFactory` that reads `.plzma` front-coded streams
directly instead of building a full `dict[bytes, bytes]` in RAM.

Front-coding is sequential (each record delta-encodes the previous), so random
access needs restart points: one pass builds a sparse per-block seed index,
then each lookup bisects to a block and decodes only its few records.

Trades much lower RAM (several-fold, more for larger dicts) for slower lookups
(~4x end-to-end through `Lemmatizer`'s cache): for memory-bound multi-language
use, not throughput.
"""

from bisect import bisect_right
from itertools import islice
from collections.abc import Iterator, Mapping

from . import frontcode
from .dictionary_factory import (
    CachingDictionaryFactory,
    DecodedStrMapping,
    SUPPORTED_LANGUAGES,
    _read_decompressed,
)

_BLOCK_SIZE = 64


class StreamMap(DecodedStrMapping):
    """Read-only str->str view over a front-coded stream, decoded on demand.

    `_firsts` holds each block's first key (for bisect); `_blocks` holds the
    matching (offset, prev_key, prev_value) to resume decoding that block.
    """

    __slots__ = ("_data", "_pos", "_rev", "_count", "_firsts", "_blocks")

    def __init__(self, lang: str) -> None:
        self._data = _read_decompressed(lang)
        self._rev, self._count, self._pos = frontcode.read_header(self._data)

        firsts: list[bytes] = []
        blocks: list[tuple[int, bytes, bytes]] = []
        prev_key, prev_value = b"", b""
        for index, (record_start, stored_key, stored_value) in enumerate(
            frontcode.iter_records(self._data, self._pos)
        ):
            if index % _BLOCK_SIZE == 0:
                firsts.append(stored_key)
                blocks.append((record_start, prev_key, prev_value))
            prev_key, prev_value = stored_key, stored_value
        self._firsts = firsts
        self._blocks = blocks

    def _lookup(self, key: str) -> str | None:
        target = key.encode()
        if self._rev:
            target = target[::-1]

        block = bisect_right(self._firsts, target) - 1
        if block < 0:
            return None

        offset, prev_key, prev_value = self._blocks[block]
        records = frontcode.iter_records(self._data, offset, prev_key, prev_value)
        for _, stored_key, stored_value in islice(records, _BLOCK_SIZE):
            if stored_key == target:
                value = stored_value[::-1] if self._rev else stored_value
                return value.decode()
            if stored_key > target:
                return None
        return None

    def __iter__(self) -> Iterator[str]:
        for _, stored_key, _ in frontcode.iter_records(self._data, self._pos):
            key = stored_key[::-1] if self._rev else stored_key
            yield key.decode()

    def __len__(self) -> int:
        return self._count


class StreamDictionaryFactory(CachingDictionaryFactory):
    """Memory-optimized `DictionaryFactory` backed by direct front-coded
    stream reads (see module docstring for the RAM/speed trade-off).
    """

    __slots__ = ()

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return StreamMap(lang)
