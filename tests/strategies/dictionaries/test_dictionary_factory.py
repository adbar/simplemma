import lzma

import pytest

from simplemma.strategies import DefaultDictionaryFactory
from simplemma.strategies.dictionaries import frontcode
from simplemma.strategies.dictionaries.dictionary_factory import (
    MappingStrToByteString,
)


def test_decode_rejects_non_frontcoded_payload() -> None:
    blob = lzma.compress(b"\x80\x05 legacy pickle bytes, no SMFC1 magic")
    with pytest.raises(ValueError, match="front-coded"):
        frontcode._decode_stream(lzma.decompress(blob))


def test_mapping_str_to_bytestring() -> None:
    """A bytes dict exposed through a str interface."""
    raw = {"chats".encode(): "chat".encode(), "préférées".encode(): "préféré".encode()}
    mapping = MappingStrToByteString(raw)

    assert mapping["chats"] == "chat"
    assert mapping["préférées"] == "préféré"
    assert len(mapping) == 2
    assert sorted(mapping) == ["chats", "préférées"]
    assert "chats" in mapping
    assert dict(mapping) == {"chats": "chat", "préférées": "préféré"}
    with pytest.raises(KeyError):
        mapping["unknown"]


def test_exceptions() -> None:
    dictionary_factory = DefaultDictionaryFactory()
    with pytest.raises(ValueError):
        dictionary_factory.get_dictionary("abc")


def test_dictionary_cache() -> None:
    iterations = 10
    dictionaries = DefaultDictionaryFactory()
    for _ in range(iterations):
        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("de")
    assert dictionaries._get_dictionary.cache_info().misses == 2
    assert dictionaries._get_dictionary.cache_info().hits == (iterations - 1) * 2
    assert dictionaries.get_dictionary("en") is dictionaries.get_dictionary("en")
