import io
import lzma
import pickle

import pytest

from simplemma.strategies import DefaultDictionaryFactory
from simplemma.strategies.dictionaries import frontcode
from simplemma.strategies.dictionaries.dictionary_factory import (
    MappingStrToByteString,
)


def test_load_rejects_non_dict_legacy_pickle() -> None:
    # a legacy (non-front-coded) .plzma payload that isn't a dict: frontcode.load
    # falls through to pickle.load and must reject it. (Shipped dicts are now
    # front-coded, so this exercises the legacy-pickle branch directly.)
    blob = lzma.compress(pickle.dumps(["not", "a", "dict"]))
    with lzma.open(io.BytesIO(blob), "rb") as fh:
        with pytest.raises(TypeError, match="unexpected data"):
            frontcode.load(fh)


def test_mapping_str_to_bytestring() -> None:
    """The wrapper exposes a bytes->bytes dict through a str->str interface."""
    raw = {"chats".encode(): "chat".encode(), "préférées".encode(): "préféré".encode()}
    mapping = MappingStrToByteString(raw)

    # __getitem__ transparently encodes the key and decodes the value
    assert mapping["chats"] == "chat"
    assert mapping["préférées"] == "préféré"
    # __len__
    assert len(mapping) == 2
    # __iter__ yields decoded str keys
    assert sorted(mapping) == ["chats", "préférées"]
    # Mapping mixins built on top of the three methods above
    assert "chats" in mapping
    assert dict(mapping) == {"chats": "chat", "préférées": "préféré"}
    with pytest.raises(KeyError):
        mapping["unknown"]


def test_exceptions() -> None:
    # missing languages or faulty language codes
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
    # the cached wrapper itself is reused, not just the underlying dict
    assert dictionaries.get_dictionary("en") is dictionaries.get_dictionary("en")
