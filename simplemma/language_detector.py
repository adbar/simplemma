"""Experimental language detection."""

from operator import itemgetter
from typing import Dict, List, Tuple, Union

from .strategies.lemmatization_strategy import LemmatizationStrategy
from .strategies.default import DefaultStrategy

from .dictionary_factory import DictionaryFactory
from .token_sampler import (
    TokenSampler,
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
)


def in_target_language(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_sampler: TokenSampler = MostCommonTokenSampler(),
) -> float:
    """Determine which proportion of the text is in the target language(s)."""
    return LanguageDetector(
        lang, dictionary_factory, token_sampler, DefaultStrategy(greedy)
    ).proportion_in_target_languages(text)


def langdetect(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    token_samplers: List[TokenSampler] = [
        MostCommonTokenSampler(),
        RelaxedMostCommonTokenSampler(),
    ],
) -> List[Tuple[str, float]]:
    """Determine which proportion of the text is in the target language(s)."""
    for token_sampler in token_samplers:
        results = LanguageDetector(
            lang, dictionary_factory, token_sampler, DefaultStrategy(greedy)
        ).proportion_in_each_language(text)

        # post-processing
        list_results = _as_list(results)
        if len(list_results) == 1 or list_results[0][1] != list_results[1][1]:
            return list_results
    return list_results


def _as_list(results: Dict[str, float]) -> List[Tuple[str, float]]:
    "Convert the results to a sorted list and switch unknown to the end."
    list_results: List[Tuple[str, float]] = sorted(
        results.items(), key=itemgetter(1), reverse=True
    )
    for i, item in enumerate(list_results):
        if item[0] == "unk":
            pair = list_results.pop(i)
            list_results.append(pair)
            break
    return list_results


class LanguageDetector:
    __slots__ = [
        "dictionary_factory",
        "greedy",
        "lang",
        "lemmatization_strategy",
        "_orig_token_sampler",
        "token_sampler",
    ]

    def __init__(
        self,
        lang: Union[str, Tuple[str, ...]],
        dictionary_factory: DictionaryFactory = DictionaryFactory(),
        token_sampler: TokenSampler = MostCommonTokenSampler(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
    ) -> None:
        self.lang = lang
        self.dictionary_factory = dictionary_factory
        self.token_sampler = token_sampler
        self._orig_token_sampler = token_sampler
        self.lemmatization_strategy = lemmatization_strategy

    def _restore_token_sampler(self) -> None:
        self.token_sampler = self._orig_token_sampler

    def proportion_in_each_language(
        self,
        text: str,
    ) -> Dict[str, float]:
        """Determine which proportion of the text is in each of the target language(s)."""
        tokens = self.token_sampler.sample_text(text)

        total_tokens = len(tokens)
        if total_tokens == 0:
            return {"unk": 1}

        dictionaries = self.dictionary_factory.get_dictionaries(self.lang)
        known_tokens_count = dict.fromkeys(dictionaries, 0)
        unknown_tokens_count = 0
        for token in tokens:
            token_found = False
            for lang_code, lang_dictionary in dictionaries.items():
                candidate = self.lemmatization_strategy.get_lemma(
                    token, lang_code, lang_dictionary
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
    ) -> float:
        return sum(
            percentage
            for (
                lang_code,
                percentage,
            ) in self.proportion_in_each_language(text).items()
            if lang_code != "unk"
        )

    def main_language(
        self,
        text: str,
        additional_token_samplers: List[TokenSampler] = [
            RelaxedMostCommonTokenSampler()
        ],
    ) -> str:
        token_samplers = [self.token_sampler] + additional_token_samplers

        for token_sampler in token_samplers:
            self.token_sampler = token_sampler
            list_results = _as_list(self.proportion_in_each_language(text))
            if len(list_results) > 1 and list_results[0][1] != list_results[1][1]:
                self._restore_token_sampler()
                return list_results[0][0]

        self._restore_token_sampler()
        return "unk"
