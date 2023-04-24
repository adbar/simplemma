from typing import Optional

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy


class NoneFallbackStrategy(LemmatizationFallbackStrategy):
    def __init__(self, greedy: bool = False):
        self.greedy = greedy

    def get_lemma(self, token: str, lang: str) -> str:
        raise ValueError(f"Token not found: {token}")
