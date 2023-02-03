from simplemma.dictionary_factory import DictionaryFactory


def test_dictionary_cache() -> None:
    iterations = 10
    dictionaries = DictionaryFactory()
    for _ in range(iterations):
        dictionaries.get_dictionaries("en")
        dictionaries.get_dictionaries("de")
    assert dictionaries._load_dictionary_from_disk.cache_info().misses == 2
    assert (
        dictionaries._load_dictionary_from_disk.cache_info().hits
        == (iterations - 1) * 2
    )
