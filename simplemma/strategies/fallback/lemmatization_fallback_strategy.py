from abc import ABC, abstractmethod


class LemmatizationFallbackStrategy(ABC):
    @abstractmethod
    def get_lemma(self, token: str, lang: str) -> str:
        raise NotImplementedError()
