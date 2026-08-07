from collections.abc import ItemsView, Iterator, KeysView
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

try:
    from marisa_trie import BytesTrie

    HAS_MARISA = True
except ImportError:
    HAS_MARISA = False

from simplemma.strategies.dictionaries.trie_dictionary_factory import TrieWrapDict
from simplemma.strategies import TrieDictionaryFactory

if not HAS_MARISA:
    pytest.skip("skipping marisa-trie tests", allow_module_level=True)


@contextmanager
def _spy_trie_io(
    factory: TrieDictionaryFactory,
) -> Iterator[tuple[MagicMock, MagicMock]]:
    """Spy on trie building and disk writes while keeping the real behavior."""
    with (
        patch.object(
            TrieDictionaryFactory, "_build_trie", wraps=factory._build_trie
        ) as build,
        patch.object(
            TrieDictionaryFactory,
            "_write_trie_to_disk",
            wraps=factory._write_trie_to_disk,
        ) as write,
    ):
        yield build, write


def test_import_error_without_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "simplemma.strategies.dictionaries.trie_dictionary_factory._TRIE_DEPS_AVAILABLE",
        False,
    )
    with pytest.raises(ImportError, match="marisa_trie and platformdirs"):
        TrieDictionaryFactory()


def test_exceptions() -> None:
    # missing languages or faulty language codes
    dictionary_factory = TrieDictionaryFactory(use_disk_cache=False)
    with pytest.raises(ValueError, match="Unsupported language"):
        dictionary_factory.get_dictionary("abc")


def test_dictionary_lru_cache() -> None:
    iterations = 10
    dictionaries = TrieDictionaryFactory(use_disk_cache=False)
    for _ in range(iterations):
        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("eo")
    assert dictionaries._get_dictionary.cache_info().misses == 2
    assert dictionaries._get_dictionary.cache_info().hits == (iterations - 1) * 2


def test_max_lru_cache_size() -> None:
    dictionaries = TrieDictionaryFactory(cache_max_size=3, use_disk_cache=False)

    for lang in ["eo", "en", "en", "ga", "tl", "cy", "eo"]:
        dictionaries.get_dictionary(lang)

    assert dictionaries._get_dictionary.cache_info().misses == 6
    assert dictionaries._get_dictionary.cache_info().hits == 1


def test_no_disk_cache(tmp_path: Path) -> None:
    dictionaries = TrieDictionaryFactory(
        use_disk_cache=False, disk_cache_dir=str(tmp_path)
    )

    with _spy_trie_io(dictionaries) as (create_trie_mock, write_trie_mock):
        assert sorted(tmp_path.iterdir()) == []

        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("fr")

        dictionaries.get_dictionary("en")
        dictionaries.get_dictionary("fr")

        create_trie_mock.assert_has_calls([call("en"), call("fr")])
        write_trie_mock.assert_not_called()

        assert sorted(tmp_path.iterdir()) == []


def test_disk_cache(tmp_path: Path) -> None:
    dictionaries = TrieDictionaryFactory(disk_cache_dir=str(tmp_path))

    with _spy_trie_io(dictionaries) as (create_trie_mock, write_trie_mock):
        assert sorted(tmp_path.iterdir()) == []

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

        assert sorted(tmp_path.iterdir()) == [
            tmp_path / "en.dic",
            tmp_path / "fr.dic",
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

        assert sorted(tmp_path.iterdir()) == [
            tmp_path / "en.dic",
            tmp_path / "fr.dic",
        ]


def test_corrupted_disk_cache(tmp_path: Path) -> None:
    dictionaries = TrieDictionaryFactory(disk_cache_dir=str(tmp_path))

    with _spy_trie_io(dictionaries) as (create_trie_mock, write_trie_mock):
        assert sorted(tmp_path.iterdir()) == []

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

        assert sorted(tmp_path.iterdir()) == [
            tmp_path / "en.dic",
        ]

        with (tmp_path / "en.dic").open("wb") as f:
            f.write(b"corrupted trie dictionary")
        dictionaries._get_dictionary.cache_clear()

        # Loading a corrupted file should regenerate it.
        dictionaries.get_dictionary("en")

        create_trie_mock.assert_called_once_with("en")
        write_trie_mock.assert_called_once()

        assert sorted(tmp_path.iterdir()) == [tmp_path / "en.dic"]


def test_write_failure_removes_partial_file(tmp_path: Path) -> None:
    dictionaries = TrieDictionaryFactory(disk_cache_dir=str(tmp_path))
    mock_trie = MagicMock()
    mock_trie.save.side_effect = OSError("disk full")
    with pytest.raises(OSError, match="disk full"):
        dictionaries._write_trie_to_disk("en", mock_trie)
    assert sorted(tmp_path.iterdir()) == []


def test_write_failure_still_returns_dictionary(tmp_path: Path) -> None:
    dictionaries = TrieDictionaryFactory(disk_cache_dir=str(tmp_path))
    with patch.object(
        TrieDictionaryFactory,
        "_write_trie_to_disk",
        side_effect=OSError("disk full"),
    ):
        result = dictionaries.get_dictionary("en")
    assert result.get("balconies") == "balcony"


def test_disabled_disk_cache_ignores_existing_file(tmp_path: Path) -> None:
    # Pre-populate a cache file with a disk-cache-enabled factory.
    TrieDictionaryFactory(disk_cache_dir=str(tmp_path)).get_dictionary("en")

    dictionaries = TrieDictionaryFactory(
        disk_cache_dir=str(tmp_path), use_disk_cache=False
    )
    with patch.object(
        TrieDictionaryFactory,
        "_build_trie",
        wraps=dictionaries._build_trie,
    ) as create_trie_mock:
        dictionaries.get_dictionary("en")
    # use_disk_cache=False must rebuild, not load the existing file.
    create_trie_mock.assert_called_once_with("en")


def test_disk_cache_creates_nested_dir(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    dictionaries = TrieDictionaryFactory(disk_cache_dir=str(nested))
    dictionaries.get_dictionary("en")
    assert (nested / "en.dic").exists()


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
        wrapped_trie["balconies123"]
    assert wrapped_trie.get("balconies") == "balcony"
    assert wrapped_trie.get("balconies123") is None

    assert isinstance(wrapped_trie.keys(), KeysView)
    assert isinstance(wrapped_trie.items(), ItemsView)
    assert len(wrapped_trie) == 3

    # read-only Mapping: assignment/deletion unsupported
    with pytest.raises(TypeError):
        wrapped_trie["houses"] = "teapot"
    with pytest.raises(TypeError):
        del wrapped_trie["balconies"]

    assert [key for key in wrapped_trie] == ["balconies", "houses", "ponies"]
