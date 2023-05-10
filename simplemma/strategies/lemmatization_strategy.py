from typing import Dict, Optional
from abc import ABC, abstractmethod


class LemmatizationStrategy(ABC):
    @abstractmethod
    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        raise NotImplementedError()
