"""
Language detector module.
Provides classes for text language detection using lemmatization and token sampling.

- [LanguageDetector][simplemma.language_detector.LanguageDetector]: Class for performing language detection using lemmatization and token sampling.
- [in_target_language()][simplemma.language_detector.in_target_language]: A legacy function that wraps the LanguageDetector's [proportion_in_target_languages()][simplemma.language_detector.LanguageDetector.proportion_in_target_languages] method.
- [langdetect()][simplemma.language_detector.langdetect]: A legacy function that wraps the LanguageDetector's [proportion_in_each_language()][simplemma.language_detector.LanguageDetector.proportion_in_each_language] method.
"""

from operator import itemgetter

from .strategies import DefaultStrategy, LemmatizationStrategy
from .token_sampler import (
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
    TokenSampler,
)
from .utils import normalize_token, validate_lang_input


def in_target_language(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    token_sampler: TokenSampler | None = None,
) -> float:
    """
    Calculate the proportion of text in the target language(s).

    Args:
        text (str): The input text to analyze.
        lang (str | tuple[str, ...]): The target language(s) to compare against.
        greedy (bool, optional): Whether to use greedy lemmatization. Defaults to `False`.
        token_sampler (TokenSampler, optional): The token sampling strategy to use.
            Defaults to `MostCommonTokenSampler()`.

    Returns:
        float: The proportion of text in the target language(s).
    """
    if token_sampler is None:
        token_sampler = MostCommonTokenSampler()

    return LanguageDetector(
        lang, token_sampler, DefaultStrategy(greedy)
    ).proportion_in_target_languages(text)


def langdetect(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    token_samplers: list[TokenSampler] | None = None,
) -> list[tuple[str, float]]:
    """
    Detect the language(s) of the given text and their proportions.

    Args:
        text (str): The input text to analyze.
        lang (str | tuple[str, ...]): The target language(s) to compare against.
        greedy (bool, optional): Whether to use greedy lemmatization. Defaults to `False`.
        token_samplers (list[TokenSampler], optional): The list of token sampling strategies
            to use. Defaults to `[MostCommonTokenSampler(), RelaxedMostCommonTokenSampler()]`.

    Returns:
        list[tuple[str, float]]: A list of tuples containing the detected language(s)
            and their respective proportions.
    """
    if token_samplers is None:
        token_samplers = [MostCommonTokenSampler(), RelaxedMostCommonTokenSampler()]

    list_results: list[tuple[str, float]] = []
    for token_sampler in token_samplers:
        results = LanguageDetector(
            lang, token_sampler, DefaultStrategy(greedy)
        ).proportion_in_each_language(text)

        # post-processing
        list_results = _as_list(results)
        if len(list_results) == 1 or list_results[0][1] != list_results[1][1]:
            return list_results
    return list_results


def _as_list(results: dict[str, float]) -> list[tuple[str, float]]:
    """
    Convert the language detection results into a sorted list.

    Args:
        results (dict[str, float]): The language detection results.

    Returns:
        list[tuple[str, float]]: A sorted list of tuples containing the language codes
            and their respective proportions.
    """
    list_results: list[tuple[str, float]] = sorted(
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
        "_token_sampler",
    ]

    def __init__(
        self,
        lang: str | tuple[str, ...],
        token_sampler: TokenSampler = MostCommonTokenSampler(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
    ) -> None:
        """
        Initialize the LanguageDetector.

        Args:
            lang (str | tuple[str, ...]): The target language or languages to detect.
            token_sampler (TokenSampler, optional): The token sampling strategy to use.
                Defaults to `MostCommonTokenSampler()`.
            lemmatization_strategy (LemmatizationStrategy, optional): The lemmatization
                strategy to use. `Defaults to DefaultStrategy()`.
        """

        self._lang = validate_lang_input(lang)
        self._token_sampler = token_sampler
        self._lemmatization_strategy = lemmatization_strategy

    def proportion_in_each_language(
        self,
        text: str,
        token_sampler: TokenSampler | None = None,
    ) -> dict[str, float]:
        """
        Calculate the proportion of each language in the given text.

        Args:
            text (str): The input text to analyze.
            token_sampler (TokenSampler, optional): Override the instance's token
                sampler for this call. Passing it keeps the call stateless, so a
                shared detector is safe to use concurrently. Defaults to the
                instance's sampler.

        Returns:
            dict[str, float]: A dictionary containing the detected languages and
                their respective proportions.
        """
        tokens = (token_sampler or self._token_sampler).sample_text(text)

        total_tokens = len(tokens)
        if total_tokens == 0:
            return {"unk": 1}

        known_tokens_count, found_any = self._count_known_tokens(tokens)
        results: dict[str, float] = {
            lang_code: token_count / total_tokens
            for (lang_code, token_count) in known_tokens_count.items()
        }
        results["unk"] = found_any.count(False) / total_tokens
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

        _, found_any = self._count_known_tokens(tokens)
        return found_any.count(True) / len(tokens)

    def _count_known_tokens(
        self, tokens: list[str]
    ) -> tuple[dict[str, int], list[bool]]:
        """Count how many sampled tokens each language recognizes.

        Loops languages-outer so each language's dictionary is loaded once and
        reused across every token, instead of being reloaded per token when the
        candidate count exceeds the dictionary cache. Results are identical to a
        tokens-outer scan.

        Returns:
            A per-language count of recognized tokens, plus a parallel list
            flagging each token recognized by at least one language (used for the
            unknown tally and the target-language proportion).
        """
        tokens = [normalize_token(token) for token in tokens]
        known_tokens_count: dict[str, int] = {}
        found_any = [False] * len(tokens)
        for lang_code in self._lang:
            count = 0
            for index, token in enumerate(tokens):
                if self._lemmatization_strategy.get_lemma(token, lang_code) is not None:
                    count += 1
                    found_any[index] = True
            known_tokens_count[lang_code] = count
        return known_tokens_count, found_any

    def main_language(
        self,
        text: str,
        additional_token_samplers: list[TokenSampler] | None = None,
    ) -> str:
        """
        Determine the main language of the given text.

        Args:
            text (str): The input text to analyze.
            additional_token_samplers (list[TokenSampler], optional): Additional token
                sampling strategies to use. Defaults to `[RelaxedMostCommonTokenSampler()]`.

        Returns:
            str: The main language of the text.
        """
        if additional_token_samplers is None:
            additional_token_samplers = [RelaxedMostCommonTokenSampler()]

        for token_sampler in [self._token_sampler, *additional_token_samplers]:
            list_results = _as_list(
                self.proportion_in_each_language(text, token_sampler)
            )
            if len(list_results) > 1 and list_results[0][1] != list_results[1][1]:
                return list_results[0][0]

        return "unk"
