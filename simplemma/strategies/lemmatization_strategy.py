from typing import Dict, Optional, Protocol


class LemmatizationStrategy(Protocol):
    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        raise NotImplementedError()
