"""
Lemmatizer module.
Provides classes for text language detection using lemmatization and token sampling.

- [LanguageDetector][simplemma.language_detector.LanguageDetector]: Class for performing language detection using lemmatization and token sampling.
- [in_target_language()][simplemma.language_detector.in_target_language]: A legacy function that wraps the LanguageDetector's [is_known()][simplemma.language_detector.LanguageDetector.proportion_in_each_language] method.
- [langdetect()][simplemma.language_detector.langdetect]: A legacy function that wraps the LanguageDetector's [is_known()][simplemma.language_detector.LanguageDetector.proportion_in_target_languages] method.
"""

from operator import itemgetter
from typing import Dict, List, Tuple, Union

from .strategies import DefaultStrategy, LemmatizationStrategy
from .token_sampler import (
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
    TokenSampler,
)
from .utils import validate_lang_input


def in_target_language(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    token_sampler: TokenSampler = MostCommonTokenSampler(),
) -> float:
    """
    Calculate the proportion of text in the target language(s).

    Args:
        text (str): The input text to analyze.
        lang (Union[str, Tuple[str, ...]]): The target language(s) to compare against.
        greedy (bool, optional): Whether to use greedy lemmatization. Defaults to `False`.
        token_sampler (TokenSampler, optional): The token sampling strategy to use.
            Defaults to `MostCommonTokenSampler()`.

    Returns:
        float: The proportion of text in the target language(s).
    """

    return LanguageDetector(
        lang, token_sampler, DefaultStrategy(greedy)
    ).proportion_in_target_languages(text)


def langdetect(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    token_samplers: List[TokenSampler] = [
        MostCommonTokenSampler(),
        RelaxedMostCommonTokenSampler(),
    ],
) -> List[Tuple[str, float]]:
    """
    Detect the language(s) of the given text and their proportions.

    Args:
        text (str): The input text to analyze.
        lang (Union[str, Tuple[str, ...]]): The target language(s) to compare against.
        greedy (bool, optional): Whether to use greedy lemmatization. Defaults to `False`.
        token_samplers (List[TokenSampler], optional): The list of token sampling strategies
            to use. Defaults to `[MostCommonTokenSampler(), RelaxedMostCommonTokenSampler()]`.

    Returns:
        List[Tuple[str, float]]: A list of tuples containing the detected language(s)
            and their respective proportions.
    """

    for token_sampler in token_samplers:
        results = LanguageDetector(
            lang, token_sampler, DefaultStrategy(greedy)
        ).proportion_in_each_language(text)

        # post-processing
        list_results = _as_list(results)
        if len(list_results) == 1 or list_results[0][1] != list_results[1][1]:
            return list_results
    return list_results


def _as_list(results: Dict[str, float]) -> List[Tuple[str, float]]:
    """
    Convert the language detection results into a sorted list.

    Args:
        results (Dict[str, float]): The language detection results.

    Returns:
        List[Tuple[str, float]]: A sorted list of tuples containing the language codes
            and their respective proportions.
    """
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
    """A class that performs language detection using lemmatization and token sampling."""

    __slots__ = [
        "_lang",
        "_lemmatization_strategy",
        "_orig_token_sampler",
        "_token_sampler",
    ]

    def __init__(
        self,
        lang: Union[str, Tuple[str, ...]],
        token_sampler: TokenSampler = MostCommonTokenSampler(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
    ) -> None:
        """
        Initialize the LanguageDetector.

        Args:
            lang (Union[str, Tuple[str, ...]]): The target language or languages to detect.
            token_sampler (TokenSampler, optional): The token sampling strategy to use.
                Defaults to `MostCommonTokenSampler()`.
            lemmatization_strategy (LemmatizationStrategy, optional): The lemmatization
                strategy to use. `Defaults to DefaultStrategy()`.
        """

        self._lang = validate_lang_input(lang)
        self._token_sampler = token_sampler
        self._orig_token_sampler = token_sampler
        self._lemmatization_strategy = lemmatization_strategy

    def _restore_token_sampler(self) -> None:
        self._token_sampler = self._orig_token_sampler

    def proportion_in_each_language(
        self,
        text: str,
    ) -> Dict[str, float]:
        """
        Calculate the proportion of each language in the given text.

        Args:
            text (str): The input text to analyze.

        Returns:
            Dict[str, float]: A dictionary containing the detected languages and
                their respective proportions.
        """
        tokens = self._token_sampler.sample_text(text)

        total_tokens = len(tokens)
        if total_tokens == 0:
            return {"unk": 1}

        known_tokens_count = dict.fromkeys(self._lang, 0)
        unknown_tokens_count = 0
        for token in tokens:
            token_found = False
            for lang_code in self._lang:
                candidate = self._lemmatization_strategy.get_lemma(token, lang_code)
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
        """
        Calculate the proportion of text in the target language.

        Args:
            text (str): The input text to analyze.

        Returns:
            float: The proportion of text in the target language(s).
        """
        tokens = self._token_sampler.sample_text(text)
        if len(tokens) == 0:
            return 0

        in_target = 0
        for token in tokens:
            for lang_code in self._lang:
                candidate = self._lemmatization_strategy.get_lemma(token, lang_code)
                if candidate is not None:
                    in_target += 1
                    break
        return in_target / len(tokens)

    def main_language(
        self,
        text: str,
        additional_token_samplers: List[TokenSampler] = [
            RelaxedMostCommonTokenSampler()
        ],
    ) -> str:
        """
        Determine the main language of the given text.

        Args:
            text (str): The input text to analyze.
            additional_token_samplers (List[TokenSampler], optional): Additional token
                sampling strategies to use. Defaults to `[RelaxedMostCommonTokenSampler()]`.

        Returns:
            str: The main language of the text.
        """
        token_samplers = [self._token_sampler] + additional_token_samplers

        for token_sampler in token_samplers:
            self._token_sampler = token_sampler
            list_results = _as_list(self.proportion_in_each_language(text))
            if len(list_results) > 1 and list_results[0][1] != list_results[1][1]:
                self._restore_token_sampler()
                return list_results[0][0]

        self._restore_token_sampler()
        return "unk"
