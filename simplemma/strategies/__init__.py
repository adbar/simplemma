"""Simplemma strategies module"""

from .affix_decomposition import AffixDecompositionStrategy
from .default import DefaultStrategy
from .dictionaries import (
    DefaultDictionaryFactory,
    DictionaryFactory,
    TrieDictionaryFactory,
)
from .dictionary_lookup import DictionaryLookupStrategy
from .fallback.lemmatization_fallback_strategy import LemmatizationFallbackStrategy
from .fallback.raise_error import RaiseErrorFallbackStrategy
from .fallback.to_lowercase import ToLowercaseFallbackStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .lemmatization_strategy import LemmatizationStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .rules import RulesStrategy

__all__ = [
    "AffixDecompositionStrategy",
    "DefaultStrategy",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "TrieDictionaryFactory",
    "DictionaryLookupStrategy",
    "LemmatizationFallbackStrategy",
    "RaiseErrorFallbackStrategy",
    "ToLowercaseFallbackStrategy",
    "GreedyDictionaryLookupStrategy",
    "HyphenRemovalStrategy",
    "LemmatizationStrategy",
    "PrefixDecompositionStrategy",
    "RulesStrategy",
]
