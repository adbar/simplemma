"""Language detection via lemmatization and token sampling."""

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
    token_sampler: TokenSampler = MostCommonTokenSampler(),
    low_memory: bool = False,
) -> float:
    """Proportion of `text` recognized in the target language(s)."""
    return LanguageDetector(
        lang, token_sampler, DefaultStrategy(greedy, low_memory=low_memory)
    ).proportion_in_target_languages(text)


def langdetect(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    token_samplers: list[TokenSampler] | None = None,
    low_memory: bool = False,
) -> list[tuple[str, float]]:
    """Per-language proportions, sorted descending; ties broken by a relaxed sampler."""
    if token_samplers is None:
        token_samplers = [MostCommonTokenSampler(), RelaxedMostCommonTokenSampler()]

    list_results: list[tuple[str, float]] = []
    for token_sampler in token_samplers:
        results = LanguageDetector(
            lang, token_sampler, DefaultStrategy(greedy, low_memory=low_memory)
        ).proportion_in_each_language(text)

        # post-processing
        list_results = _as_list(results)
        if len(list_results) == 1 or list_results[0][1] != list_results[1][1]:
            return list_results
    return list_results


def _as_list(results: dict[str, float]) -> list[tuple[str, float]]:
    """Sort language detection results descending by score, ``"unk"`` last."""
    return sorted(results.items(), key=lambda item: (item[0] == "unk", -item[1]))


class LanguageDetector:
    """Language detection via dictionary membership probing."""

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
        self._lang = validate_lang_input(lang)
        self._token_sampler = token_sampler
        self._lemmatization_strategy = lemmatization_strategy

    def proportion_in_each_language(self, text: str) -> dict[str, float]:
        """Per-language share of recognized tokens."""
        return self._proportion_in_each_language(text, self._token_sampler)

    def _proportion_in_each_language(
        self,
        text: str,
        token_sampler: TokenSampler,
    ) -> dict[str, float]:
        """Per-language proportions for a given sampler.

        Sampler is an arg (not self's) so the call stays stateless for
        ``main_language``. Loops languages-outer to load each dictionary once
        instead of thrashing the cache per token.
        """
        tokens = [normalize_token(token) for token in token_sampler.sample_text(text)]

        total_tokens = len(tokens)
        if total_tokens == 0:
            return {"unk": 1}

        results: dict[str, float] = {}
        found_any = [False] * total_tokens
        for lang_code in self._lang:
            count = 0
            for index, token in enumerate(tokens):
                if self._lemmatization_strategy.get_lemma(token, lang_code) is not None:
                    count += 1
                    found_any[index] = True
            results[lang_code] = count / total_tokens

        results["unk"] = found_any.count(False) / total_tokens
        return results

    def proportion_in_target_languages(self, text: str) -> float:
        """Share of tokens recognized in any of the target languages."""
        tokens = self._token_sampler.sample_text(text)
        if len(tokens) == 0:
            return 0

        # only "recognized by any language" matters, so break on first match
        in_target = 0
        for token in tokens:
            token = normalize_token(token)
            for lang_code in self._lang:
                if self._lemmatization_strategy.get_lemma(token, lang_code) is not None:
                    in_target += 1
                    break
        return in_target / len(tokens)

    def main_language(
        self,
        text: str,
        additional_token_samplers: list[TokenSampler] | None = None,
    ) -> str:
        """Winning language, or ``"unk"`` on a tie or no recognition."""
        if additional_token_samplers is None:
            additional_token_samplers = [RelaxedMostCommonTokenSampler()]

        for token_sampler in [self._token_sampler, *additional_token_samplers]:
            list_results = _as_list(
                self._proportion_in_each_language(text, token_sampler)
            )
            if len(list_results) > 1 and list_results[0][1] != list_results[1][1]:
                return list_results[0][0]

        return "unk"
