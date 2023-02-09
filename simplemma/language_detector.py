"""Experimental language detection."""

import re

from collections import Counter
from operator import itemgetter
from typing import Dict, List, Optional, Tuple, Union

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


def in_target_language(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_sampler: TokenSampler = TokenSampler(),
) -> float:
    """Determine which proportion of the text is in the target language(s)."""
    return LanguageDetector(
        dictionary_factory, token_sampler
    ).get_text_percentage_in_all_languages(text, lang, greedy)


def _convert_results_to_sorted_list(
    results: Dict[str, float]
) -> List[Tuple[str, float]]:
    list_results: List[Tuple[str, float]] = sorted(
        results.items(), key=itemgetter(1), reverse=True
    )
    # switch unknown to the end
    for i, item in enumerate(list_results):
        if item[0] == "unk":
            pair = list_results.pop(i)
            list_results.append(pair)
    return list_results


def lang_detector(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_sampler: TokenSampler = TokenSampler(),
    backup_sampler: TokenSampler = TokenSampler(
        tokenizer=Tokenizer(RELAXED_SPLIT_INPUT),
        max_tokens=1000,
        capitalized_threshold=0,
    ),
) -> List[Tuple[str, float]]:
    """Determine which proportion of the text is in the target language(s)."""
    results = LanguageDetector(
        dictionary_factory, token_sampler
    ).get_text_percentage_in_each_languages(text, lang, greedy)
    # post-processing
    if len(results) == 1:
        return _convert_results_to_sorted_list(results)
    # in case of ex-aequo
    list_results = _convert_results_to_sorted_list(results)
    if greedy is False and list_results[0][1] == list_results[1][1]:
        results = LanguageDetector(
            dictionary_factory, token_sampler
        ).get_text_percentage_in_each_languages(text, lang, greedy=True)

    list_results = _convert_results_to_sorted_list(results)
    # in case of ex-aequo use other token sampling to discriminate
    if not greedy and list_results[0][1] == list_results[1][1]:
        results = LanguageDetector(
            dictionary_factory, backup_sampler
        ).get_text_percentage_in_each_languages(text, lang, greedy=True)

    list_results = _convert_results_to_sorted_list(results)
    return list_results


class LanguageDetector:
    __slots__ = ["dictionary_factory", "token_sampler"]

    def __init__(
        self,
        dictionary_factory: DictionaryFactory = DictionaryFactory(),
        token_sampler: TokenSampler = TokenSampler(),
    ) -> None:
        self.dictionary_factory = dictionary_factory
        self.token_sampler = token_sampler

    def get_text_percentage_in_each_languages(
        self,
        text: str,
        lang: Optional[Union[str, Tuple[str, ...]]] = None,
        greedy: bool = False,
    ) -> Dict[str, float]:
        """Determine which proportion of the text is in the target language(s).
        Perform a first run and further discriminate between the results if necessary.
        """

        tokens = self.token_sampler.sample_tokens(text)
        total_tokens = len(tokens)
        if total_tokens == 0:
            return {"unk": 1}
        # iterate
        dictionaries = self.dictionary_factory.get_dictionaries(lang)
        known_tokens_count = dict.fromkeys(dictionaries, 0)
        unknown_tokens_count = 0
        for token in tokens:
            token_found = False
            for lang_code, lang_dictionary in dictionaries.items():
                candidate = _return_lemma(
                    token, lang_dictionary, greedy=greedy, lang=lang_code
                )
                if candidate is not None:
                    known_tokens_count[lang_code] += 1
                    token_found = True
            if not token_found:
                unknown_tokens_count += 1

        results: Dict[str, float] = dict(
            (lang_code, token_count / total_tokens)
            for (lang_code, token_count) in known_tokens_count.items()
        )
        results["unk"] = unknown_tokens_count / total_tokens
        return results

    def get_text_percentage_in_all_languages(
        self,
        text: str,
        lang: Optional[Union[str, Tuple[str, ...]]] = None,
        greedy: bool = False,
    ) -> float:
        """Determine which proportion of the text is in the target language(s)."""

        return 1 - self.get_text_percentage_in_each_languages(text, lang, greedy)["unk"]
