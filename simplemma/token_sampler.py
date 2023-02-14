import re


from typing import List
from collections import Counter
from .tokenizer import Tokenizer

SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")
RELAXED_SPLIT_INPUT = re.compile(r"[\w-]{3,}")


class TokenSampler:
    __slots__ = ["capitalized_threshold", "max_tokens", "tokenizer"]

    def __init__(
        self,
        tokenizer: Tokenizer = Tokenizer(SPLIT_INPUT),
        max_tokens: int = 100,
        capitalized_threshold: float = 0.8,
    ) -> None:
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.capitalized_threshold = capitalized_threshold

    def sample_tokens(self, text: str) -> List[str]:
        """Extract potential tokens, scramble them, potentially get rid of capitalized
        ones, and return the most frequent."""

        counter = Counter(token for token in self.tokenizer.split_text(text))

        if self.capitalized_threshold > 0:
            deletions = [token for token in counter if token[0].isupper()]
            if len(deletions) < self.capitalized_threshold * len(counter):
                for token in deletions:
                    del counter[token]

        return [item[0] for item in counter.most_common(self.max_tokens)]
