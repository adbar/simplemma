"""Main module."""

import logging
import re

from functools import lru_cache
from typing import Any, Dict, List, Iterator, Optional, Tuple, Union

from .constants import CACHE_SIZE
from .dictionary_factory import DictionaryFactory
from .tokenizer import Tokenizer
from .rules import APPLY_RULES, FIND_KNOWN_PREFIXES
from .utils import levenshtein_dist


LOGGER = logging.getLogger(__name__)

AFFIXLEN = 2
LONGAFFIXLEN = 5  # better for some languages
MINCOMPLEN = 4

BETTER_LOWER = {"bg", "es", "hy", "lt", "lv", "pt", "sk", "uk"}

# TODO: This custom behavior has to be simplified before it becomes unmaintainable
LONGER_AFFIXES = {"et", "fi", "hu", "lt"}
SHORTER_GREEDY = {"bg", "et", "fi"}
AFFIX_LANGS = {
    "bg",
    "cs",
    "el",
    "et",
    "fi",
    "hu",
    "hy",
    "lt",
    "lv",
    "nb",
    "pl",
    "ru",
    "sk",
    "tr",
    "uk",
}

HYPHENS = {"-", "_"}
HYPHENS_FOR_REGEX = "".join(HYPHENS)
HYPHEN_REGEX = re.compile(rf"([{HYPHENS_FOR_REGEX}])")
PUNCTUATION = {".", "?", "!", "…", "¿", "¡"}


def _simple_search(
    token: str, datadict: Dict[str, str], initial: bool = False
) -> Optional[str]:
    "Search the language data, reverse case to extend coverage."
    # beginning of sentence, reverse case
    if initial:
        token = token.lower()
    if token in datadict:
        return datadict[token]
    # try upper or lowercase
    token = token.lower() if token[0].isupper() else token.capitalize()
    return datadict.get(token)


def _greedy_search(
    token: str, datadict: Dict[str, str], steps: int = 1, distance: int = 5
) -> str:
    "Greedy mode: try further hops, not always a good idea."
    candidate = token
    for _ in range(steps):
        if candidate not in datadict:
            break

        new_candidate = datadict[candidate]

        if (
            len(new_candidate) > len(candidate)
            or levenshtein_dist(new_candidate, candidate) > distance
        ):
            break

        candidate = new_candidate

    return candidate


def _dehyphen_search(token: str, datadict: Dict[str, str]) -> Optional[str]:
    "Remove hyphens to see if a dictionary form can be found."
    token_parts = HYPHEN_REGEX.split(token)
    if len(token_parts) <= 1 or not token_parts[-1]:
        return None

    # try to find a word form without hyphen
    candidate = "".join([t for t in token_parts if t not in HYPHENS]).lower()
    if token[0].isupper():
        candidate = candidate.capitalize()
    if candidate in datadict:
        return datadict[candidate]

    # decompose
    last_candidate = _simple_search(token_parts[-1], datadict)
    if last_candidate is not None:
        token_parts[-1] = last_candidate
        return "".join(token_parts)

    return None


def _apply_rules(token: str, lang: Optional[str]) -> Optional[str]:
    "Apply simple rules to out-of-vocabulary words."
    if lang not in APPLY_RULES:
        return None

    return APPLY_RULES[lang](token)

def _prefix_search(
    token: str, lang: Optional[str], datadict: Dict[str, str]
) -> Optional[str]:
    "Subword decomposition using pre-defined prefixes (often absent from vocabulary if they are not words)."
    if lang not in FIND_KNOWN_PREFIXES:
        return None

    prefix = FIND_KNOWN_PREFIXES[lang](token)
    if prefix is None:
        return None

    subword = _simple_search(token[len(prefix) :], datadict)
    if subword is None:
        return None

    return prefix + subword.lower()


def _affix_search(
    token: str,
    datadict: Dict[str, str],
    max_affix_len: int = 0,
    min_complem_len: int = 0,
) -> Optional[str]:
    "Split token into known two known parts and lemmatize the second one."
    # this only makes sense for languages written from left to right
    # AFFIXLEN or MINCOMPLEN can spare time for some languages
    for affixlen in range(max_affix_len, 1, -1):
        for count in range(1, len(token) - min_complem_len + 1):
            part1 = token[:-count]
            # part1_aff = candidate[:-(count + affixlen)]
            lempart1 = _simple_search(part1, datadict)
            if lempart1 is None:
                continue
            # maybe an affix? discard it
            if count <= affixlen:
                return lempart1
            # account for case before looking for second part
            part2 = token[-count:]
            if token[0].isupper():
                part2 = part2.capitalize()
            lempart2 = _simple_search(part2, datadict)
            if lempart2 is None:
                continue
            # candidate must be shorter
            # try other case
            candidate = _greedy_search(part2, datadict)
            # shorten the second known part of the token
            if candidate is not None and len(candidate) < len(part2):
                return part1 + candidate.lower()
            # backup: equal length or further candidates accepted
            # try without capitalizing
            # even greedier
            # with capital letter?
            if len(lempart2) < len(part2) + affixlen:
                return part1 + lempart2.lower()
                # print(part1, part2, affixlen, count, newcandidate, planb)
            # elif newcandidate and len(newcandidate) < len(part2) + affixlen:
            # plan_b = part1 + newcandidate.lower()
            # print(part1, part2, affixlen, count, newcandidate, planb)
            # else:
            #    print(part1, part2, affixlen, count, newcandidate)
    return None


def _suffix_search(
    token: str, datadict: Dict[str, str], min_complem_len: int = 0
) -> Optional[str]:
    for count in range(len(token) - min_complem_len, min_complem_len - 1, -1):
        suffix = _simple_search(token[-count:].capitalize(), datadict)
        if suffix is not None and len(suffix) <= len(token[-count:]):
            return token[:-count] + suffix.lower()

    return None


def _affix_searches(
    token: str, greedy: bool, limit: int, lang: Optional[str], datadict: Dict[str, str]
) -> Optional[str]:
    "Unsupervised suffix/affix search, not productive for all languages."
    if (not greedy and not lang in AFFIX_LANGS) or len(token) <= limit:
        return None

    # define parameters
    max_affix_len = LONGAFFIXLEN if lang in LONGER_AFFIXES else AFFIXLEN
    # greedier subword decomposition: suffix search with character in between
    # then suffixes
    return _affix_search(token, datadict, max_affix_len, MINCOMPLEN) or _suffix_search(
        token, datadict, MINCOMPLEN
    )


def _return_lemma(
    token: str,
    datadict: Dict[str, str],
    greedy: bool = True,
    lang: Optional[str] = None,
    initial: bool = False,
) -> Optional[str]:
    "Apply a cascade of functions on a token to look for a candidate lemma."
    # filters
    if token.isnumeric():
        return token

    limit = 6 if lang in SHORTER_GREEDY else 8

    candidate = (
        # supervised searches
        _simple_search(token, datadict, initial=initial)
        or _dehyphen_search(token, datadict)
        or _apply_rules(token, lang)
        or _prefix_search(token, lang, datadict)
        # weakly supervised / greedier searches
        or _affix_searches(token, greedy, limit, lang, datadict)
    )

    # additional round
    if candidate is not None and greedy and len(token) > limit:
        candidate = _greedy_search(candidate, datadict)

    return candidate


def _control_input_type(token: Any) -> None:
    "Make sure the input is a string of length > 0."
    if not isinstance(token, str):
        raise TypeError(f"Wrong input type, expected string, got {type(token)}")
    if token == "":
        raise ValueError("Wrong input type: empty string")


def is_known(
    token: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
) -> bool:
    """Tell if a token is present in one of the loaded dictionaries.
    Case-insensitive, whole word forms only. Returns True or False."""
    _control_input_type(token)
    dictionaries = dictionary_factory.get_dictionaries(lang)  # ignore returned value
    return any(
        _simple_search(token, language_dictionary) is not None
        for language_dictionary in dictionaries.values()
    )


def _lemmatize(
    token: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    silent: bool = True,
    initial: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
) -> str:
    """Try to reduce a token to its lemma form according to the
    language list passed as input.
    Returns a string.
    Can raise ValueError by silent=False if no lemma has been found."""
    _control_input_type(token)
    dictionaries = dictionary_factory.get_dictionaries(lang)  # use returned lang value
    # start
    for i, (lang_code, lang_dictionary) in enumerate(dictionaries.items(), start=1):
        # determine default greediness
        # if greedy is None:
        #    greedy = _define_greediness(language)
        # determine lemma
        candidate = _return_lemma(
            token, lang_dictionary, greedy=greedy, lang=lang_code, initial=initial
        )
        if candidate is not None:
            if i != 1:
                LOGGER.debug("%s found in %s", token, lang_code)
            return candidate
    if not silent:
        raise ValueError(f"Token not found: {token}")
    # try to simply lowercase # and len(token) < 10 ?
    return token.lower() if next(iter(dictionaries)) in BETTER_LOWER else token


# provide drop-in replacement for previously decorated function
lemmatize = lru_cache(maxsize=CACHE_SIZE)(_lemmatize)


def text_lemmatizer(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    silent: bool = True,
) -> List[str]:
    """Convenience function to lemmatize a text using a simple tokenizer.
    Returns a list of tokens and lemmata."""
    return list(lemma_iterator(text, lang, greedy, silent))


def lemma_iterator(
    text: str,
    lang: Optional[Union[str, Tuple[str, ...]]] = None,
    greedy: bool = False,
    silent: bool = True,
    tokenizer: Tokenizer = Tokenizer(),
) -> Iterator[str]:
    """Convenience function to lemmatize a text using a simple tokenizer.
    Returns a list of tokens and lemmata."""
    initial = True
    for token in tokenizer.split_text(text):
        yield lemmatize(token, lang, greedy, silent, initial)
        initial = token in PUNCTUATION
