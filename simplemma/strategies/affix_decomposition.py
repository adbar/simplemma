from typing import Dict, Optional

from .lemmatization_strategy import LemmatizationStrategy
from .dictionary_lookup import DictionaryLookupStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy

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
    def __init__(
        self,
        greedy: bool,
        limit: int,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
        greedy_dictionary_lookup: GreedyDictionaryLookupStrategy = GreedyDictionaryLookupStrategy(),
    ):
        self.greedy = greedy
        self.limit = limit
        self.dictionary_lookup = dictionary_lookup
        self.greedy_dictionary_lookup = greedy_dictionary_lookup

    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        "Unsupervised suffix/affix search, not productive for all languages."
        if (not self.greedy and not lang in AFFIX_LANGS) or len(token) <= self.limit:
            return None

        # define parameters
        max_affix_len = LONGAFFIXLEN if lang in LONGER_AFFIXES else AFFIXLEN
        # greedier subword decomposition: suffix search with character in between
        # then suffixes
        return self._affix_decomposition(
            token, lang, dictionary, max_affix_len, MINCOMPLEN
        ) or self._suffix_decomposition(token, lang, dictionary, MINCOMPLEN)

    def _affix_decomposition(
        self,
        token: str,
        lang: str,
        dictionary: Dict[str, str],
        max_affix_len: int = 0,
        min_complem_len: int = 0,
    ) -> Optional[str]:
        "Split token into known two known parts and lemmatize the second one."
        # this only makes sense for languages written from left to right
        # AFFIXLEN or MINCOMPLEN can spare time for some languages
        for affixlen in range(max_affix_len, 1, -1):
            for count in range(1, len(token) - min_complem_len + 1):
                part1 = token[:-count]
                # part1_aff = candidate[:-(count + affixlen)]
                lempart1 = self.dictionary_lookup.get_lemma(part1, lang, dictionary)
                if lempart1 is None:
                    continue
                # maybe an affix? discard it
                if count <= affixlen:
                    return lempart1
                # account for case before looking for second part
                part2 = token[-count:]
                if token[0].isupper():
                    part2 = part2.capitalize()
                lempart2 = self.dictionary_lookup.get_lemma(part2, lang, dictionary)
                if lempart2 is None:
                    continue
                # candidate must be shorter
                # try other case
                candidate = self.greedy_dictionary_lookup.get_lemma(
                    part2, lang, dictionary
                )
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
        dictionary: Dict[str, str],
        min_complem_len: int = 0,
    ) -> Optional[str]:
        for count in range(len(token) - min_complem_len, min_complem_len - 1, -1):
            suffix = self.dictionary_lookup.get_lemma(
                token[-count:].capitalize(), lang, dictionary
            )
            if suffix is not None and len(suffix) <= len(token[-count:]):
                return token[:-count] + suffix.lower()

        return None
