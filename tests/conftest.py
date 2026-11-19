from collections.abc import Iterable, Mapping
from typing import Any

from simplemma import BaseTokenSampler
from simplemma.strategies import DictionaryFactory
from training import ud_conllu


class FixedMapping(DictionaryFactory):
    """Serves the same fixed str->str mapping for every language."""

    def __init__(self, mapping: Mapping[str, str]) -> None:
        self._mapping = mapping

    def get_dictionary(self, lang: str) -> Mapping[str, str]:
        return self._mapping


def conllu(sentences: Iterable[Iterable[tuple[Any, ...]]]) -> str:
    """Minimal CoNLL-U from (id, form, lemma[, upos]) rows, upos defaulting to 'X'."""
    blocks = []
    for rows in sentences:
        lines = [
            "\t".join(
                [str(r[0]), r[1], r[2], r[3] if len(r) > 3 else "X"]
                + ["_", "_", "0", "root", "_", "_"]
            )
            for r in rows
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n\n"


def write_licenses(monkeypatch, tmp_path, **licenses: str) -> None:
    """Point UD_LICENSES at a file mapping each dataset name to its license."""
    path = tmp_path / "licenses.tsv"
    path.write_text("".join(f"{k}\t{v}\n" for k, v in licenses.items()))
    monkeypatch.setattr(ud_conllu, "UD_LICENSES", path)


class CustomTokenSampler(BaseTokenSampler):
    """Drops the first `skip_tokens` tokens."""

    def __init__(self, skip_tokens: int) -> None:
        super().__init__()
        self.skip_tokens: int = skip_tokens

    def sample_tokens(self, tokens: Iterable[str]) -> list[str]:
        return list(tokens)[self.skip_tokens :]
