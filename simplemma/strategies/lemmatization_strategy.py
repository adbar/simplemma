from typing import Dict, Optional
from abc import ABC


class LemmatizationStrategy(ABC):
    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        raise NotImplementedError()
