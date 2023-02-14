"""Experimental language detection."""

from operator import itemgetter
from typing import Dict, List, Optional, Tuple, Union

from .lemmatizer import _return_lemma
from .dictionary_factory import DictionaryFactory
from .token_sampler import TokenSampler, RELAXED_SPLIT_INPUT
from .tokenizer import Tokenizer


def in_target_language(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_sampler: TokenSampler = TokenSampler(),
) -> float:
    """Determine which proportion of the text is in the target language(s)."""
    return LanguageDetector(
        lang, greedy, dictionary_factory
    ).proportion_in_target_languages(text, token_sampler)


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


def langdetect(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_samplers: List[TokenSampler] = [
        TokenSampler(),
        TokenSampler(
            tokenizer=Tokenizer(RELAXED_SPLIT_INPUT),
            max_tokens=1000,
            capitalized_threshold=0,
        ),
    ],
) -> List[Tuple[str, float]]:
    """Determine which proportion of the text is in the target language(s)."""
    for token_sampler in token_samplers:
        results = LanguageDetector(
            lang, greedy, dictionary_factory
        ).proportion_in_each_language(text, token_sampler)
        list_results = _convert_results_to_sorted_list(results)

        # post-processing
        if len(list_results) == 1 or list_results[0][1] != list_results[1][1]:
            return list_results
    return list_results


class LanguageDetector:
    __slots__ = ["dictionary_factory", "greedy", "lang"]

    def __init__(
        self,
        lang: Optional[Union[str, Tuple[str, ...]]] = None,
        greedy: bool = False,
        dictionary_factory: DictionaryFactory = DictionaryFactory(),
    ) -> None:
        self.lang = lang
        self.greedy = greedy
        self.dictionary_factory = dictionary_factory

    def proportion_in_each_language(
        self,
        text: str,
        token_sampler: TokenSampler = TokenSampler(),
    ) -> Dict[str, float]:
        """Determine which proportion of the text is in each of the target language(s)."""
        tokens = token_sampler.sample_tokens(text)

        total_tokens = len(tokens)
        if total_tokens == 0:
            return {"unk": 1}

        dictionaries = self.dictionary_factory.get_dictionaries(self.lang)
        known_tokens_count = dict.fromkeys(dictionaries, 0)
        unknown_tokens_count = 0
        for token in tokens:
            token_found = False
            for lang_code, lang_dictionary in dictionaries.items():
                candidate = _return_lemma(
                    token, lang_dictionary, self.greedy, lang_code
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

    def proportion_in_target_languages(
        self,
        text: str,
        token_sampler: TokenSampler = TokenSampler(),
    ) -> float:
        return sum(
            [
                percentage
                for (
                    lang_code,
                    percentage,
                ) in self.proportion_in_each_language(text, token_sampler).items()
                if lang_code != "unk"
            ]
        )

    def main_language(
        self,
        text: str,
        token_samplers: List[TokenSampler] = [
            TokenSampler(),
            TokenSampler(
                tokenizer=Tokenizer(RELAXED_SPLIT_INPUT),
                max_tokens=1000,
                capitalized_threshold=0,
            ),
        ],
    ) -> str:
        for token_sampler in token_samplers:
            results = self.proportion_in_each_language(text, token_sampler)
            list_results = _convert_results_to_sorted_list(results)
            if len(list_results) > 1 and list_results[0][1] != list_results[1][1]:
                return list_results[0][0]

        return "unk"
