import sys
from typing import Dict, Optional
from abc import abstractmethod

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class LemmatizationStrategy(Protocol):
    @abstractmethod
    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        raise NotImplementedError()
