import sys
from abc import abstractmethod

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class LemmatizationFallbackStrategy(Protocol):
    @abstractmethod
    def get_lemma(self, token: str, lang: str) -> str:
        raise NotImplementedError()
