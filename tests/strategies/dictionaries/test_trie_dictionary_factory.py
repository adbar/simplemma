from collections.abc import ItemsView, KeysView
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import call, patch

import pytest

try:
    from marisa_trie import BytesTrie  # type: ignore[import-not-found]

    HAS_MARISA = True
except ImportError:
    HAS_MARISA = False

from simplemma.strategies.dictionaries.trie_directory_factory import TrieWrapDict
from simplemma.strategies import TrieDictionaryFactory


if not HAS_MARISA:
    pytest.skip("skipping marisa-trie tests", allow_module_level=True)


def test_exceptions() -> None:
    # missing languages or faulty language codes
    dictionary_factory = TrieDictionaryFactory(use_disk_cache=False)
    with pytest.raises(ValueError):
        dictionary_factory.get_dictionary(("abc"))


def test_dictionary_lru_cache() -> None:
    iterations = 10
    dictionaries = TrieDictionaryFactory(use_disk_cache=False)
    for _ in range(iterations):
        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("de")
    assert dictionaries._get_dictionary.cache_info().misses == 2
    assert dictionaries._get_dictionary.cache_info().hits == (iterations - 1) * 2


def test_max_lru_cache_size() -> None:
    dictionaries = TrieDictionaryFactory(cache_max_size=3, use_disk_cache=False)

    for lang in ["de", "en", "en", "es", "fr", "it", "de"]:
        dictionaries.get_dictionary(lang)

    assert dictionaries._get_dictionary.cache_info().misses == 6
    assert dictionaries._get_dictionary.cache_info().hits == 1


def test_disabled_disk_cache() -> None:
    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        dictionaries = TrieDictionaryFactory(
            disk_cache_dir=tmp_dir, use_disk_cache=False
        )
        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("fr")
        assert sorted(tmp_dir_path.iterdir()) == []


def test_no_disk_cache() -> None:
    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        dictionaries = TrieDictionaryFactory(
            use_disk_cache=False, disk_cache_dir=tmp_dir
        )

        with patch.object(
            TrieDictionaryFactory,
            "_create_trie_from_pickled_dict",
            wraps=dictionaries._create_trie_from_pickled_dict,
        ) as create_trie_mock, patch.object(
            TrieDictionaryFactory,
            "_write_trie_to_disk",
            wraps=dictionaries._write_trie_to_disk,
        ) as write_trie_mock:
            assert sorted(tmp_dir_path.iterdir()) == []

            dictionaries.get_dictionary("en")
            dictionaries.get_dictionary("fr")

            dictionaries.get_dictionary("en")
            dictionaries.get_dictionary("fr")

            create_trie_mock.assert_has_calls([call("en"), call("fr")])
            write_trie_mock.assert_not_called()

            assert sorted(tmp_dir_path.iterdir()) == []


def test_disk_cache() -> None:
    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        dictionaries = TrieDictionaryFactory(disk_cache_dir=tmp_dir)

        with patch.object(
            TrieDictionaryFactory,
            "_create_trie_from_pickled_dict",
            wraps=dictionaries._create_trie_from_pickled_dict,
        ) as create_trie_mock, patch.object(
            TrieDictionaryFactory,
            "_write_trie_to_disk",
            wraps=dictionaries._write_trie_to_disk,
        ) as write_trie_mock:
            assert sorted(tmp_dir_path.iterdir()) == []

            # Initial cached trie files should be generated.
            en_dictionary = dictionaries.get_dictionary("en")
            fr_dictionary = dictionaries.get_dictionary("fr")

            create_trie_mock.assert_has_calls([call("en"), call("fr")])
            create_trie_mock.reset_mock()
            write_trie_mock.assert_has_calls(
                [
                    call("en", en_dictionary._trie),  # type: ignore[attr-defined]
                    call("fr", fr_dictionary._trie),  # type: ignore[attr-defined]
                ]
            )
            write_trie_mock.reset_mock()

            assert sorted(tmp_dir_path.iterdir()) == [
                tmp_dir_path / "en.dic",
                tmp_dir_path / "fr.dic",
            ]

            # LRU cache should result in not checking for cached tries.
            dictionaries.get_dictionary("en")
            dictionaries.get_dictionary("fr")

            create_trie_mock.assert_not_called()
            write_trie_mock.assert_not_called()

            dictionaries._get_dictionary.cache_clear()

            # Cached trie files should be checked, but not regenerated,
            # as LRU cached got emptied.
            dictionaries.get_dictionary("en")
            dictionaries.get_dictionary("fr")

            create_trie_mock.assert_not_called()
            write_trie_mock.assert_not_called()

            assert sorted(tmp_dir_path.iterdir()) == [
                tmp_dir_path / "en.dic",
                tmp_dir_path / "fr.dic",
            ]


def test_corrupted_disk_cache() -> None:
    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        dictionaries = TrieDictionaryFactory(disk_cache_dir=tmp_dir)

        with patch.object(
            TrieDictionaryFactory,
            "_create_trie_from_pickled_dict",
            wraps=dictionaries._create_trie_from_pickled_dict,
        ) as create_trie_mock, patch.object(
            TrieDictionaryFactory,
            "_write_trie_to_disk",
            wraps=dictionaries._write_trie_to_disk,
        ) as write_trie_mock:
            assert sorted(tmp_dir_path.iterdir()) == []

            # Initial cached trie file should be generated.
            en_dictionary = dictionaries.get_dictionary("en")

            create_trie_mock.assert_has_calls([call("en")])
            create_trie_mock.reset_mock()
            write_trie_mock.assert_has_calls(
                [
                    call("en", en_dictionary._trie),  # type: ignore[attr-defined]
                ]
            )
            write_trie_mock.reset_mock()

            assert sorted(tmp_dir_path.iterdir()) == [
                tmp_dir_path / "en.dic",
            ]

            with (tmp_dir_path / "en.dic").open("wb") as f:
                f.write(b"corrupted trie dictionary")
            dictionaries._get_dictionary.cache_clear()

            # Loading a corrupted hash should regenerate it.
            with pytest.raises(RuntimeError):
                dictionaries.get_dictionary("en")

            create_trie_mock.assert_not_called()
            write_trie_mock.assert_not_called()

            assert sorted(tmp_dir_path.iterdir()) == [tmp_dir_path / "en.dic"]


def test_dictionary_working_as_a_dict() -> None:
    dictionaries = TrieDictionaryFactory(use_disk_cache=False)
    dictionary = dictionaries.get_dictionary("en")

    assert isinstance(dictionary, TrieWrapDict)

    assert ("balconies" in dictionary) is True
    assert ("balconies123" in dictionary) is False
    with pytest.raises(KeyError):
        dictionary["balconies123"]
    assert dictionary.get("balconies") == "balcony"


def test_trie_wrap_dict():
    trie = BytesTrie(
        zip(["houses", "balconies", "ponies"], [b"house", b"balcony", b"pony"])
    )
    wrapped_trie = TrieWrapDict(trie)

    assert ("balconies" in wrapped_trie) is True
    assert ("balconies123" in wrapped_trie) is False
    assert wrapped_trie["balconies"] == "balcony"
    with pytest.raises(KeyError):
        wrapped_trie[b"balconies123"]
    assert wrapped_trie.get("balconies") == "balcony"
    assert wrapped_trie.get("balconies123") is None

    assert isinstance(wrapped_trie.keys(), KeysView)
    assert isinstance(wrapped_trie.items(), ItemsView)
    assert len(wrapped_trie) == 3

    with pytest.raises(NotImplementedError):
        wrapped_trie["houses"] = "teapot"
    with pytest.raises(NotImplementedError):
        del wrapped_trie["balconies"]

    assert [key for key in wrapped_trie] == ["balconies", "houses", "ponies"]
