from typing import Set

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy

BETTER_LOWER = {"bg", "es", "hy", "lt", "lv", "pt", "sk", "uk"}


class ToLowercaseFallbackStrategy(LemmatizationFallbackStrategy):
    __slots__ = ["_langs_to_lower"]

    def __init__(self, langs_to_lower: Set[str] = BETTER_LOWER):
        self._langs_to_lower = langs_to_lower

    def get_lemma(self, token: str, lang: str) -> str:
        return token.lower() if lang in BETTER_LOWER else token
