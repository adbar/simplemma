from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy


class RaiseErrorFallbackStrategy(LemmatizationFallbackStrategy):
    def get_lemma(self, token: str, lang: str) -> str:
        raise ValueError(f"Token not found: {token}")
