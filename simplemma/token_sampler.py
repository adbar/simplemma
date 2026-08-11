"""Token sampling: select representative tokens from text for language detection."""

import re
from abc import ABC, abstractmethod
from collections import Counter
from typing import Protocol
from collections.abc import Iterable

from .tokenizer import RegexTokenizer, Tokenizer

SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")
RELAXED_SPLIT_INPUT = re.compile(r"[\w-]{3,}")


class TokenSampler(Protocol):
    """Protocol for token samplers used in language detection."""

    __slots__ = ()

    @abstractmethod
    def sample_text(self, text: str) -> list[str]:
        """Tokenize text and return a sample of its tokens."""
        raise NotImplementedError

    @abstractmethod
    def sample_tokens(self, tokens: Iterable[str]) -> list[str]:
        """Return a sample of the given tokens."""
        raise NotImplementedError


class BaseTokenSampler(ABC, TokenSampler):
    """Tokenize text then delegate to `sample_tokens`."""

    __slots__ = ["_tokenizer"]

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(SPLIT_INPUT),
    ) -> None:
        self._tokenizer = tokenizer

    def sample_text(self, text: str) -> list[str]:
        return self.sample_tokens(self._tokenizer.split_text(text))


class MostCommonTokenSampler(BaseTokenSampler):
    """Select the most common tokens, optionally removing capitalized ones."""

    __slots__ = ["_capitalized_threshold", "_sample_size"]

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(SPLIT_INPUT),
        sample_size: int = 100,
        capitalized_threshold: float = 0.8,
    ) -> None:
        super().__init__(tokenizer)
        self._sample_size = sample_size
        self._capitalized_threshold = capitalized_threshold

    def sample_tokens(self, tokens: Iterable[str]) -> list[str]:
        counter = Counter(tokens)

        if self._capitalized_threshold > 0:
            deletions = [token for token in counter if token[:1].isupper()]
            if len(deletions) < self._capitalized_threshold * len(counter):
                for token in deletions:
                    del counter[token]

        return [item[0] for item in counter.most_common(self._sample_size)]


class RelaxedMostCommonTokenSampler(MostCommonTokenSampler):
    """MostCommonTokenSampler with a more relaxed regex and no capitalization filter."""

    __slots__ = ()

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(RELAXED_SPLIT_INPUT),
        sample_size: int = 1000,
        capitalized_threshold: float = 0,
    ) -> None:
        super().__init__(tokenizer, sample_size, capitalized_threshold)
