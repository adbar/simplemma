"""
Sampler module. Provides classes for sampling tokens from text.

- TokenSampler: An abstract base class for token samplers.
- BaseTokenSampler: A base class for token samplers with common functionality.
- MostCommonTokenSampler: A token sampler that selects the most common tokens.
- RelaxedMostCommonTokenSampler: A relaxed version of the most common token sampler.

"""

import re
import sys
from abc import ABC, abstractmethod
from typing import Iterable, List
from collections import Counter
from .tokenizer import Tokenizer, RegexTokenizer

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")
RELAXED_SPLIT_INPUT = re.compile(r"[\w-]{3,}")


class TokenSampler(Protocol):
    """
    Abstract base class for token samplers.

    Token samplers are used to sample tokens from text.

    """

    @abstractmethod
    def sample_text(self, text: str) -> List[str]:
        """
        Sample tokens from the input text.

        Args:
            text (str): The input text to sample tokens from.

        Returns:
            List[str]: The sampled tokens.

        """
        raise NotImplementedError

    @abstractmethod
    def sample_tokens(self, tokens: Iterable[str]) -> List[str]:
        """
        Sample tokens from the given iterable of tokens.

        Args:
            tokens (Iterable[str]): The iterable of tokens to sample from.

        Returns:
            List[str]: The sampled tokens.

        """
        raise NotImplementedError


class BaseTokenSampler(ABC, TokenSampler):
    """
    BaseTokenSampler is the base class for token samplers.
    It uses the given Tokenizer to convert a text in token.
    Classes inheriting from BaseTokenSampler only have to implement sample_tokens.

    Args:
        tokenizer (Tokenizer, optional): The tokenizer to use for splitting text into tokens.
            Defaults to `RegexTokenizer(SPLIT_INPUT)`.

    Methods:
        sample_text(text: str) -> List[str]:
            Samples tokens from the given text.

        sample_tokens(tokens: List[str]) -> List[str]:
            Samples tokens from the given list of tokens.
    """

    __slots__ = ["_tokenizer"]

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(SPLIT_INPUT),
    ) -> None:
        """
        Initialize the BaseTokenSampler.

        Args:
            tokenizer (Tokenizer, optional): The tokenizer to use for splitting text into tokens.
                Defaults to `RegexTokenizer(SPLIT_INPUT)`.
        """
        self._tokenizer = tokenizer

    def sample_text(self, text: str) -> List[str]:
        """
        Sample tokens from the input text.

        Args:
            text (str): The input text to sample tokens from.

        Returns:
            List[str]: The sampled tokens.

        """
        return self.sample_tokens(self._tokenizer.split_text(text))

    @abstractmethod
    def sample_tokens(self, tokens: Iterable[str]) -> List[str]:
        """
        Sample tokens from the given iterable of tokens.

        Args:
            tokens (Iterable[str]): The iterable of tokens to sample from.

        Returns:
            List[str]: The sampled tokens.

        """
        raise NotImplementedError


class MostCommonTokenSampler(BaseTokenSampler):
    """
    Token sampler that selects the most common tokens.

    Methods:
        sample_text(text: str) -> List[str]:
            Samples tokens from the given text.

        sample_tokens(tokens: List[str]) -> List[str]:
            Samples tokens from the given list of tokens.
    """

    __slots__ = ["_capitalized_threshold", "_sample_size"]

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(SPLIT_INPUT),
        sample_size: int = 100,
        capitalized_threshold: float = 0.8,
    ) -> None:
        """
        Initialize the MostCommonTokenSampler.

        Args:
            tokenizer (Tokenizer, optional): The tokenizer to use for splitting text into tokens.
                Defaults to `RegexTokenizer(SPLIT_INPUT)`.
            sample_size (int, optional): The number of tokens to sample. Defaults to `100`.
            capitalized_threshold (float, optional): The threshold for removing capitalized tokens.
                Tokens with a frequency greater than this threshold will be removed. Defaults to `0.8`.
        """
        super().__init__(tokenizer)
        self._sample_size = sample_size
        self._capitalized_threshold = capitalized_threshold

    def sample_tokens(self, tokens: Iterable[str]) -> List[str]:
        """
        Sample tokens from the given iterable of tokens.

        Args:
            tokens (Iterable[str]): The iterable of tokens to sample from.

        Returns:
            List[str]: The sampled tokens.

        """
        counter = Counter(tokens)

        if self._capitalized_threshold > 0:
            deletions = [token for token in counter if token[0].isupper()]
            if len(deletions) < self._capitalized_threshold * len(counter):
                for token in deletions:
                    del counter[token]

        return [item[0] for item in counter.most_common(self._sample_size)]


class RelaxedMostCommonTokenSampler(MostCommonTokenSampler):
    """
    Relaxed version of the most common token sampler.

    This sampler uses a relaxed splitting regex pattern and allows for a larger sample size.

    Methods:
        sample_text(text: str) -> List[str]:
            Samples tokens from the given text.

        sample_tokens(tokens: List[str]) -> List[str]:
            Samples tokens from the given list of tokens.
    """

    def __init__(
        self,
        tokenizer: Tokenizer = RegexTokenizer(RELAXED_SPLIT_INPUT),
        sample_size: int = 1000,
        capitalized_threshold: float = 0,
    ) -> None:
        """
        Initialize the RelaxedMostCommonTokenSampler.
        This is just a `MostCommonTokenSampler` with a more relaxed regex pattern.

        Args:
            tokenizer (Tokenizer, optional): The tokenizer to use for splitting text into tokens.
                Defaults to `RegexTokenizer(RELAXED_SPLIT_INPUT)`.
            sample_size (int, optional): The number of tokens to sample. Defaults to `1000`.
            capitalized_threshold (float, optional): The threshold for removing capitalized tokens.
                Tokens with a frequency greater than this threshold will be removed.
                Defaults to `0`.

        """

        super().__init__(tokenizer, sample_size, capitalized_threshold)
