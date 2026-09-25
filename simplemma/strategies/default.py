"""Default lemmatization strategy: chains all sub-strategies."""

from .affix_decomposition import AffixDecompositionStrategy
from .clitic_decomposition import CliticDecompositionStrategy
from .dictionaries import (
    DEFAULT_DICTIONARY_FACTORY,
    LOW_MEMORY_DICTIONARY_FACTORY,
    DictionaryFactory,
)
from .dictionary_lookup import DictionaryLookupStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .lemmatization_strategy import LemmatizationStrategy
from .morpheme_decomposition import MorphemeDecompositionStrategy
from .prefix_decomposition import DROP_PREFIX_LANGS, PrefixDecompositionStrategy
from .rules import RulesStrategy
from ..utils import fold_apostrophes

# Apostrophe marks a fixed morpheme boundary ("Istanbul'da"): the head is a
# proper noun or number, looked up as-is. UD-validated (tr_imst); routing the
# head through the affix chain measured worse (Güvenpark -> güven).
APOSTROPHE_BOUNDARY_LANGS = frozenset({"tr"})
MIN_HEAD_LEN = 2


def _case_key(word: str) -> str:
    return word.lower().replace("i̇", "i")


class DefaultStrategy(LemmatizationStrategy):
    """Pipeline combining dictionary lookup, clitic/hyphen/prefix/affix/morpheme
    decomposition, and per-language rules."""

    __slots__ = (
        "_dictionary_lookup",
        "_hyphen_search",
        "_rules_search",
        "_prefix_search",
        "_clitic_search",
        "_greedy_dictionary_lookup",
        "_affix_search",
        "_morpheme_search",
    )

    def __init__(
        self,
        greedy: bool = False,
        dictionary_factory: DictionaryFactory | None = None,
        low_memory: bool = False,
    ):
        if dictionary_factory is None:
            dictionary_factory = (
                LOW_MEMORY_DICTIONARY_FACTORY
                if low_memory
                else DEFAULT_DICTIONARY_FACTORY
            )
        elif low_memory:
            raise ValueError(
                "low_memory selects a dictionary_factory automatically; "
                "pass one or the other, not both"
            )
        self._dictionary_lookup = DictionaryLookupStrategy(dictionary_factory)
        self._hyphen_search = HyphenRemovalStrategy(self._dictionary_lookup)
        self._rules_search = RulesStrategy()
        self._prefix_search = PrefixDecompositionStrategy(
            dictionary_lookup=self._dictionary_lookup
        )
        self._clitic_search = CliticDecompositionStrategy(self._dictionary_lookup)
        self._affix_search = AffixDecompositionStrategy(greedy, self._dictionary_lookup)
        self._morpheme_search = MorphemeDecompositionStrategy(self._dictionary_lookup)
        self._greedy_dictionary_lookup = (
            GreedyDictionaryLookupStrategy(dictionary_factory) if greedy else None
        )

    def get_lemma(self, token: str, lang: str) -> str | None:
        if token.isnumeric():
            return token

        # particles (l'après-midi) before hyphen_search, de/ru/uk prefixes after rules
        particles_first = lang in DROP_PREFIX_LANGS
        candidate = (
            # before dictionary_lookup: its reverse-case fallback else
            # mangles capitalized proper nouns (Erdoğan'ın -> erdoğan)
            self._apostrophe_lemma(token, lang)
            or self._dictionary_lookup.get_lemma(token, lang)
            # before hyphen_search: a hyphenated clitic's last part often
            # self-resolves, so hyphen_search would return the token as-is
            or self._clitic_search.get_lemma(token, lang)
            or (self._prefix_search.get_lemma(token, lang) if particles_first else None)
            or self._hyphen_search.get_lemma(token, lang)
            or self._rules_search.get_lemma(token, lang)
            or (None if particles_first else self._prefix_search.get_lemma(token, lang))
            or self._affix_search.get_lemma(token, lang)
            or self._morpheme_search.get_lemma(token, lang)
        )
        if candidate is not None and self._greedy_dictionary_lookup is not None:
            candidate = self._greedy_dictionary_lookup.get_lemma(candidate, lang)
        return candidate

    def _apostrophe_lemma(self, token: str, lang: str) -> str | None:
        """Split at the first apostrophe and look the head up in the dictionary."""
        if lang not in APOSTROPHE_BOUNDARY_LANGS:
            return None
        boundary = fold_apostrophes(token).find("'")
        if boundary < MIN_HEAD_LEN or boundary == len(token) - 1:
            return None
        # A curated whole-token entry is authoritative over decomposition
        # (tr "isen'e" -> "isen").
        if self._dictionary_lookup.is_dictionary_member(token, lang):
            return None
        head = token[:boundary]
        if head.isnumeric():
            return head
        lemma = self._dictionary_lookup.get_lemma(head, lang)
        if lemma is None:
            return None
        # A case-only change is just the dict's case-fallback, not a real answer;
        # keep the head's case. _case_key folds Turkish "İ".lower() (i + dot).
        return head if _case_key(lemma) == _case_key(head) else lemma

    def is_dictionary_member(self, token: str, lang: str) -> bool:
        """Raw dictionary membership for `token` (no case/apostrophe fallback)."""
        return self._dictionary_lookup.is_dictionary_member(token, lang)
