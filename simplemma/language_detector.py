"""Experimental language detection."""

import re

from collections import Counter
from operator import itemgetter
from typing import List, Optional, Tuple, Union

from .lemmatizer import _return_lemma
from .dictionary_factory import DictionaryFactory
from .tokenizer import Tokenizer


SPLIT_INPUT = re.compile(r"[^\W\d_]{3,}")
RELAXED_SPLIT_INPUT = re.compile(r"[\w-]{3,}")


class TokenSampler:
    __slots__ = ["capitalized_threshold", "max_tokens", "tokenizer"]

    def __init__(
        self,
        tokenizer: Tokenizer = Tokenizer(SPLIT_INPUT),
        max_tokens: int = 1000,
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


class RelaxedTokenSampler(TokenSampler):
    def __init__(self) -> None:
        super().__init__(
            tokenizer=Tokenizer(RELAXED_SPLIT_INPUT),
            max_tokens=1000,
            capitalized_threshold=0,
        )


def in_target_language(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_sampler: TokenSampler = TokenSampler(),
) -> float:
    """Determine which proportion of the text is in the target language(s)."""
    total = 0
    in_target = 0
    dictionaries = dictionary_factory.get_dictionaries(lang)
    for token in token_sampler.sample_tokens(text):
        total += 1
        for lang_code, lang_dictionary in dictionaries.items():
            candidate = _return_lemma(
                token, lang_dictionary, greedy=True, lang=lang_code
            )
            if candidate is not None:
                in_target += 1
                break
    if total > 0 and in_target > 0:
        return in_target / total
    return 0


def _return_default() -> List[Tuple[str, float]]:
    # todo: None if 'unk'?
    return [("unk", 1)]


def lang_detector(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_sampler: TokenSampler = TokenSampler(),
    backup_sampler: TokenSampler = RelaxedTokenSampler(),
) -> List[Tuple[str, float]]:
    """Determine which proportion of the text is in the target language(s).
    Perform a first run and further discriminate between the results if necessary."""
    myresults = {}  # Dict[str, float]
    tokens = token_sampler.sample_tokens(text)
    total_tokens = len(tokens)
    if total_tokens == 0:
        return _return_default()
    # iterate
    dictionaries = dictionary_factory.get_dictionaries(lang)
    for lang_code, lang_dictionary in dictionaries.items():
        in_target = 0
        for token in tokens:
            candidate = _return_lemma(
                token, lang_dictionary, greedy=greedy, lang=lang_code
            )
            if candidate is not None:
                in_target += 1
        # compute results
        found_ratio = in_target / total_tokens
        myresults[lang_code] = found_ratio
        unknown = 1 - found_ratio or 0.0
        if myresults.get("unk") is None or unknown < myresults["unk"]:
            myresults["unk"] = unknown
    results = sorted(myresults.items(), key=itemgetter(1), reverse=True)
    # post-processing
    if len(results) > 1:
        # switch unknown first item to the end
        if results[0][0] == "unk":
            pair = results.pop(0)
            results.append(pair)
        # in case of ex-aequo use other token sampling to discriminate
        if not greedy and results[0][1] == results[1][1]:
            results = lang_detector(
                text, lang=lang, greedy=True, token_sampler=backup_sampler
            )
    return results
