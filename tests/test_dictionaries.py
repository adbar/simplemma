from simplemma.dictionaries import DictionaryCache

def test_dictionary_cache():
  iterations = 10
  dictionaries = DictionaryCache()
  for _ in range(iterations):
      dictionaries.update_lang_data("en")
      dictionaries.update_lang_data("de")
  assert dictionaries._load_pickle.cache_info().misses == 2
  assert dictionaries._load_pickle.cache_info().hits == (iterations - 1) * 2