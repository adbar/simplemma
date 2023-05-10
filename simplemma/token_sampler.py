"""TokenSampler module. A TokenSampler is a class that select samples from a text or a tokens collection."""

import re

from abc import ABC, abstractmethod
from typing import Iterable, List
from collections import Counter
from .tokenizer import Tokenizer, RegexTokenizer

SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")
RELAXED_SPLIT_INPUT = re.compile(r"[\w-]{3,}")


class TokenSampler(ABC):
    __slots__ = ["tokenizer"]

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(SPLIT_INPUT),
    ) -> None:
        self.tokenizer = tokenizer

    def sample_text(self, text: str) -> List[str]:
        return self.sample_tokens(self.tokenizer.split_text(text))

    @abstractmethod
    def sample_tokens(self, tokens: Iterable[str]) -> List[str]:
        raise NotImplementedError


class MostCommonTokenSampler(TokenSampler):
    __slots__ = ["capitalized_threshold", "sample_size"]

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(SPLIT_INPUT),
        sample_size: int = 100,
        capitalized_threshold: float = 0.8,
    ) -> None:
        super().__init__(tokenizer)
        self.sample_size = sample_size
        self.capitalized_threshold = capitalized_threshold

    def sample_text(self, text: str) -> List[str]:
        return self.sample_tokens(self.tokenizer.split_text(text))

    def sample_tokens(self, tokens: Iterable[str]) -> List[str]:
        """Extract potential tokens, scramble them, potentially get rid of capitalized
        ones, and return the most frequent."""

        counter = Counter(tokens)

        if self.capitalized_threshold > 0:
            deletions = [token for token in counter if token[0].isupper()]
            if len(deletions) < self.capitalized_threshold * len(counter):
                for token in deletions:
                    del counter[token]

        return [item[0] for item in counter.most_common(self.sample_size)]


class RelaxedMostCommonTokenSampler(MostCommonTokenSampler):
    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(RELAXED_SPLIT_INPUT),
        sample_size: int = 1000,
        capitalized_threshold: float = 0,
    ) -> None:
        super().__init__(tokenizer, sample_size, capitalized_threshold)
