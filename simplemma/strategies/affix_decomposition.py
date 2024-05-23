"""
This file defines the `AffixDecompositionStrategy` class, which implements an affix decomposition lemmatization strategy in the Simplemma library.
"""

from typing import Optional

from .dictionary_lookup import DictionaryLookupStrategy
from .greedy_dictionary_lookup import SHORTER_GREEDY, GreedyDictionaryLookupStrategy
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

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get the lemma of a token using affix decomposition strategy.

        Args:
            token (str): The input token.
            lang (str): The language code.

        Returns:
            Optional[str]: The lemma of the token if found, or None otherwise.
        """
        limit = 6 if lang in SHORTER_GREEDY else 8
        if (not self._greedy and lang not in AFFIX_LANGS) or len(token) <= limit:
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
    ) -> Optional[str]:
        """
        Perform affix decomposition on a token.

        Args:
            token (str): The input token.
            lang (str): The language code.
            max_affix_len (int): The maximum length of the affix.
            min_complem_len (int): The minimum length of the complementary part.

        Returns:
            Optional[str]: The lemma of the token if found, or None otherwise.
        """
        # this only makes sense for languages written from left to right
        # AFFIXLEN or MINCOMPLEN can spare time for some languages
        for affixlen in range(max_affix_len, 1, -1):
            for count in range(1, len(token) - min_complem_len + 1):
                part1 = token[:-count]
                # part1_aff = candidate[:-(count + affixlen)]p
                lempart1 = self._dictionary_lookup.get_lemma(part1, lang)
                if lempart1 is None:
                    continue
                # maybe an affix? discard it
                if count <= affixlen:
                    return lempart1
                # account for case before looking for second part
                part2 = token[-count:]
                if token[0].isupper():
                    part2 = part2.capitalize()
                lempart2 = self._dictionary_lookup.get_lemma(part2, lang)
                if lempart2 is None:
                    continue
                # candidate must be shorter
                # try other case
                candidate = self._greedy_dictionary_lookup.get_lemma(part2, lang)
                # shorten the second known part of the token
                if candidate is not None and len(candidate) < len(part2):
                    return part1 + candidate.lower()
                # backup: equal length or further candidates accepted
                # try without capitalizing
                # even greedier
                # with capital letter?
                if len(lempart2) < len(part2) + affixlen:
                    return part1 + lempart2.lower()
                    # print(part1, part2, affixlen, count, newcandidate, planb)
                # elif newcandidate and len(newcandidate) < len(part2) + affixlen:
                # plan_b = part1 + newcandidate.lower()
                # print(part1, part2, affixlen, count, newcandidate, planb)
                # else:
                #    print(part1, part2, affixlen, count, newcandidate)
        return None

    def _suffix_decomposition(
        self,
        token: str,
        lang: str,
        min_complem_len: int = 0,
    ) -> Optional[str]:
        """
        Decomposes the token using suffix decomposition strategy.

        Args:
            token (str): The token to be decomposed.
            lang (str): The language of the token.
            min_complem_len (int, optional): The minimum length of the complementary part
                to consider during decomposition. Defaults to 0.

        Returns:
            Optional[str]: The decomposed token if decomposition is successful, None otherwise.
        """
        for count in range(len(token) - min_complem_len, min_complem_len - 1, -1):
            suffix = self._dictionary_lookup.get_lemma(
                token[-count:].capitalize(), lang
            )
            if suffix is not None and len(suffix) <= len(token[-count:]):
                return token[:-count] + suffix.lower()

        return None
