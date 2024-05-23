import pytest

from simplemma.strategies import DefaultDictionaryFactory


def test_exceptions() -> None:
    # missing languages or faulty language codes
    dictionary_factory = DefaultDictionaryFactory()
    with pytest.raises(ValueError):
        dictionary_factory.get_dictionary(("abc"))


def test_dictionary_cache() -> None:
    iterations = 10
    dictionaries = DefaultDictionaryFactory()
    for _ in range(iterations):
        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("de")
    assert dictionaries._load_dictionary_from_disk.cache_info().misses == 2
    assert (
        dictionaries._load_dictionary_from_disk.cache_info().hits
        == (iterations - 1) * 2
    )
