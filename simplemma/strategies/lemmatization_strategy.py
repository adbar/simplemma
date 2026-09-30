"""Lemmatization strategy protocol."""

from abc import abstractmethod
from typing import Protocol


class LemmatizationStrategy(Protocol):
    """Interface for lemmatization strategies."""

    __slots__ = ()

    @abstractmethod
    def get_lemma(self, token: str, lang: str) -> str | None:
        """Return the lemma for `token` in `lang`, or None.
        Tokens are expected in NFC."""
