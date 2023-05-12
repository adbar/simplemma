from typing import Dict, Optional
from abc import ABC


class LemmatizationFallbackStrategy(ABC):
    def get_lemma(self, token: str, lang: str) -> str:
        raise NotImplementedError()
