"""Simplemma fallback strategies module"""

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy
from .raise_error import RaiseErrorFallbackStrategy
from .to_lowercase import ToLowercaseFallbackStrategy

__all__ = [
    "LemmatizationFallbackStrategy",
    "RaiseErrorFallbackStrategy",
    "ToLowercaseFallbackStrategy",
]
