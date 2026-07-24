"""Basic per-language spot-checks of PrefixDecompositionStrategy, for
languages with no distinguishing edge case beyond "does the configured
prefix list strip correctly" (see test_prefixes_ar.py/test_prefixes_he.py
for languages with real per-case nuance -- canonicalization order,
stem-floor guards -- that stays in dedicated, documented functions)."""

import pytest

from simplemma.strategies import PrefixDecompositionStrategy

_STRATEGY = PrefixDecompositionStrategy()

# (lang, form, expected-lemma-or-None)
PREFIX_CASES = [
    ("de", "zerlemmatisiertes", "zerlemmatisiert"),
    ("de", "abzugshaube", None),
    ("ru", "продолжая", "продолжать"),
    ("uk", "відкликала", "відкликати"),
]


@pytest.mark.parametrize("lang, form, expected", PREFIX_CASES)
def test_prefixes_basic(lang: str, form: str, expected: str | None) -> None:
    assert _STRATEGY.get_lemma(form, lang) == expected
