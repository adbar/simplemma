"""
This file defines the `AffixDecompositionStrategy` class, which implements an affix decomposition lemmatization strategy in the Simplemma library.
"""

from .dictionary_lookup import DictionaryLookupStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy, greedy_min_length
from .lemmatization_strategy import LemmatizationStrategy

# TODO: This custom behavior has to be simplified before it becomes unmaintainable
LONGER_AFFIXES = {"et", "fi", "hu", "lt"}
AFFIX_LANGS = {
    "bg",
    "cs",
    "el",
    "et",
    "fi",
    "hu",
    "hy",
    "lt",
    "lv",
    "nb",
    "pl",
    "ru",
    "sk",
    "tr",
    "uk",
}

AFFIXLEN = 2
LONGAFFIXLEN = 5  # better for some languages
MINCOMPLEN = 4
# Decomposition is ~O(len²); cap long tokens (longest real form is 86 chars).
MAXLEN = 100


class AffixDecompositionStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy that uses affix decomposition to find lemmas of tokens.

    This strategy decomposes tokens into affixes and looks up their lemmas in a dictionary.
    It first attempts to decompose the token using affix decomposition and then falls back
    to suffix decomposition if affix decomposition fails.
    """

    __slots__ = ["_greedy", "_dictionary_lookup", "_greedy_dictionary_lookup"]

    def __init__(
        self,
        greedy: bool,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
        greedy_dictionary_lookup: GreedyDictionaryLookupStrategy = GreedyDictionaryLookupStrategy(),
    ):
        """
        Initialize the Affix Decomposition Strategy.

        Args:
            greedy (bool): Flag indicating whether to use greedy decomposition.
            dictionary_lookup (DictionaryLookupStrategy): The dictionary lookup strategy to use.
                Defaults to `DictionaryLookupStrategy()`.
            greedy_dictionary_lookup (GreedyDictionaryLookupStrategy): The greedy dictionary lookup strategy to use.
                Defaults to `GreedyDictionaryLookupStrategy()`.
        """
        self._greedy = greedy
        self._dictionary_lookup = dictionary_lookup
        self._greedy_dictionary_lookup = greedy_dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get the lemma of a token using affix decomposition strategy.

        Args:
            token (str): The input token.
            lang (str): The language code.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        if (
            (not self._greedy and lang not in AFFIX_LANGS)
            or len(token) <= greedy_min_length(lang)
            or len(token) > MAXLEN
        ):
            return None

        # define parameters
        max_affix_len = LONGAFFIXLEN if lang in LONGER_AFFIXES else AFFIXLEN
        # greedier subword decomposition: suffix search with character in between
        # then suffixes
        return self._affix_decomposition(
            token, lang, max_affix_len, MINCOMPLEN
        ) or self._suffix_decomposition(token, lang, MINCOMPLEN)

    def _affix_decomposition(
        self,
        token: str,
        lang: str,
        max_affix_len: int = 0,
        min_complem_len: int = 0,
    ) -> str | None:
        """
        Perform affix decomposition on a token.

        Args:
            token (str): The input token.
            lang (str): The language code.
            max_affix_len (int): The maximum length of the affix.
            min_complem_len (int): The minimum length of the complementary part.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        # Left-to-right languages only. A single pass at the largest affix
        # length is equivalent to looping over smaller ones (first match wins).
        for count in range(1, len(token) - min_complem_len + 1):
            part1 = token[:-count]
            lempart1 = self._dictionary_lookup.get_lemma(part1, lang)
            if lempart1 is None:
                continue
            # maybe an affix? discard it
            if count <= max_affix_len:
                return lempart1
            # account for case before looking for second part
            part2 = token[-count:]
            if token[0].isupper():
                part2 = part2.capitalize()
            lempart2 = self._dictionary_lookup.get_lemma(part2, lang)
            if lempart2 is None:
                continue
            # prefer a shorter greedy form of the second part
            candidate = self._greedy_dictionary_lookup.get_lemma(part2, lang)
            if candidate is not None and len(candidate) < len(part2):
                return part1 + candidate.lower()
            # backup: accept the dictionary form if not longer than the affix bound
            if len(lempart2) < len(part2) + max_affix_len:
                return part1 + lempart2.lower()
        return None

    def _suffix_decomposition(
        self,
        token: str,
        lang: str,
        min_complem_len: int = 0,
    ) -> str | None:
        """
        Decomposes the token using suffix decomposition strategy.

        Args:
            token (str): The token to be decomposed.
            lang (str): The language of the token.
            min_complem_len (int, optional): The minimum length of the complementary part
                to consider during decomposition. Defaults to 0.

        Returns:
            str | None: The decomposed token if decomposition is successful, None otherwise.
        """
        for count in range(len(token) - min_complem_len, min_complem_len - 1, -1):
            suffix = self._dictionary_lookup.get_lemma(
                token[-count:].capitalize(), lang
            )
            if suffix is not None and len(suffix) <= count:
                return token[:-count] + suffix.lower()

        return None
