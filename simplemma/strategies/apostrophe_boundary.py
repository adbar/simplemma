"""
This file defines the `ApostropheBoundaryStrategy` class, which handles
languages whose orthography marks a fixed morpheme boundary with an
apostrophe (Turkish: proper-noun/suffix boundary, e.g. "Istanbul'da").
Unlike a clitic table, this is unconditional for the language: everything
after the first apostrophe is a suffix, and the head is looked up via the
REST of the pipeline (proper nouns are their own lemma; common nouns may
still need rule/affix processing on the head alone).
"""

from collections.abc import Callable

from ..utils import normalize_apostrophes
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

# UD-validated (tr_imst): the orthographic rule generalizes to open-class
# proper nouns that no lookup table can cover (plain lookup resolves ~12% of
# gold apostrophe forms). See README.md "Apostrophe/proclitic elision".
APOSTROPHE_BOUNDARY_LANGS = frozenset({"tr"})
MIN_HEAD_LEN = 2


def _case_key(word: str) -> str:
    return word.lower().replace("i̇", "i")


class ApostropheBoundaryStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy for languages where an apostrophe marks a
    fixed morpheme boundary: splits at the first apostrophe and
    lemmatizes the head via the rest of the pipeline.
    """

    __slots__ = ["_dictionary_lookup", "_lemmatize_head"]

    def __init__(
        self,
        lemmatize_head: Callable[[str, str], str | None],
        dictionary_lookup: DictionaryLookupStrategy,
    ):
        """
        Initialize the Apostrophe Boundary Strategy.

        Args:
            lemmatize_head: callback to lemmatize the head, ordinarily the
                owning `DefaultStrategy.get_lemma` (so the head gets the
                full pipeline). Injected rather than composed to avoid a
                circular construction dependency.
            dictionary_lookup: detects a curated whole-token entry, which
                is authoritative over decomposition.
        """
        self._lemmatize_head = lemmatize_head
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get the lemma of a token by splitting at the first apostrophe.

        Args:
            token (str): The input token.
            lang (str): The language code.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        if lang not in APOSTROPHE_BOUNDARY_LANGS:
            return None
        boundary = normalize_apostrophes(token).find("'")  # fold smart quotes
        if boundary < MIN_HEAD_LEN or boundary == len(token) - 1:
            return None
        # A curated whole-token entry is authoritative over decomposition
        # (tr "isen'e" -> "isen").
        if self._dictionary_lookup.exact_lemma(token, lang) is not None:
            return None
        head = token[:boundary]
        lemma = self._lemmatize_head(head, lang)
        if lemma is None:
            return None
        # A case-only change is just the dict's case-fallback, not a real answer;
        # keep the head's case. _case_key folds Turkish "İ".lower() (i + dot).
        return head if _case_key(lemma) == _case_key(head) else lemma
