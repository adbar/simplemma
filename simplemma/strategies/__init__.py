"""Simplemma strategies module"""

from .affix_decomposition import AffixDecompositionStrategy
from .apostrophe_boundary import ApostropheBoundaryStrategy
from .clitic_decomposition import CliticDecompositionStrategy
from .default import DefaultStrategy
from .dictionaries import (
    DEFAULT_DICTIONARY_FACTORY,
    LOW_MEMORY_DICTIONARY_FACTORY,
    DefaultDictionaryFactory,
    DictionaryFactory,
    StreamDictionaryFactory,
    TrieDictionaryFactory,
)
from .dictionary_lookup import DictionaryLookupStrategy
from .fallback.lemmatization_fallback_strategy import LemmatizationFallbackStrategy
from .fallback.raise_error import RaiseErrorFallbackStrategy
from .fallback.to_lowercase import ToLowercaseFallbackStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .lemmatization_strategy import LemmatizationStrategy
from .morpheme_decomposition import MorphemeDecompositionStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .rules import RulesStrategy

__all__ = [
    "AffixDecompositionStrategy",
    "ApostropheBoundaryStrategy",
    "CliticDecompositionStrategy",
    "DefaultStrategy",
    "DEFAULT_DICTIONARY_FACTORY",
    "LOW_MEMORY_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "StreamDictionaryFactory",
    "TrieDictionaryFactory",
    "DictionaryLookupStrategy",
    "LemmatizationFallbackStrategy",
    "RaiseErrorFallbackStrategy",
    "ToLowercaseFallbackStrategy",
    "GreedyDictionaryLookupStrategy",
    "HyphenRemovalStrategy",
    "LemmatizationStrategy",
    "MorphemeDecompositionStrategy",
    "PrefixDecompositionStrategy",
    "RulesStrategy",
]
