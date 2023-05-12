from typing import Optional

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy

BETTER_LOWER = {"bg", "es", "hy", "lt", "lv", "pt", "sk", "uk"}


class DefaultFallbackStrategy(LemmatizationFallbackStrategy):
    def __init__(self, greedy: bool = False):
        self.greedy = greedy

    def get_lemma(self, token: str, lang: str) -> str:
        return token.lower() if lang in BETTER_LOWER else token
