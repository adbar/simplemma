"""Basic per-language spot-checks of PrefixDecompositionStrategy."""

import pytest

from simplemma.strategies import PrefixDecompositionStrategy

_STRATEGY = PrefixDecompositionStrategy()

PREFIX_CASES = [
    ("uk", "відкликала", "відкликати"),
    ("uk", "позпрщшк", None),
]


@pytest.mark.parametrize("lang, form, expected", PREFIX_CASES)
def test_prefixes_basic(lang: str, form: str, expected: str | None) -> None:
    assert _STRATEGY.get_lemma(form, lang) == expected
