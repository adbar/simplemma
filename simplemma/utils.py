"""
Utils module.
Contains utility functions for language processing.

- [levenshtein_dist][simplemma.utils.levenshtein_dist]: Calculates the Levenshtein distance between two strings.
- [validate_lang_input][simplemma.utils.validate_lang_input]: Validates the language input and ensures it is a valid tuple.
"""

from typing import Tuple, Union


def validate_lang_input(lang: Union[str, Tuple[str, ...]]) -> Tuple[str]:
    """
    Make sure the lang variable is a valid tuple.

    Args:
        lang (Any): The language input.

    Returns:
        Tuple[str]: A tuple containing the language code.

    Raises:
        TypeError: If the lang argument is not a tuple or a string.

    """
    # convert string
    if isinstance(lang, str):
        lang = (lang,)
    if not isinstance(lang, tuple):
        raise TypeError("lang argument must be a two-letter language code")
    return lang  # type: ignore[return-value]


def levenshtein_dist(str1: str, str2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.

    The Levenshtein distance is a metric for measuring the difference between two strings,
    defined as the minimum number of single-character edits (insertions, deletions, or substitutions)
    required to change one string into the other.

    Args:
        str1 (str): The first string.
        str2 (str): The second string.

    Returns:
        int: The Levenshtein distance between the two strings.

    """
    # inspired by this noticeably faster code:
    # https://gist.github.com/p-hash/9e0f9904ce7947c133308fbe48fe032b
    if str1 == str2:
        return 0
    if len(str1) > len(str2):
        str1, str2 = str2, str1
    r1 = list(range(len(str2) + 1))
    r2 = [0] * len(r1)
    for i, c1 in enumerate(str1):
        r2[0] = i + 1
        for j, c2 in enumerate(str2):
            if c1 == c2:
                r2[j + 1] = r1[j]
            else:
                a1, a2, a3 = r2[j], r1[j], r1[j + 1]
                if a1 > a2:
                    if a2 > a3:
                        r2[j + 1] = 1 + a3
                    else:
                        r2[j + 1] = 1 + a2
                else:
                    if a1 > a3:
                        r2[j + 1] = 1 + a3
                    else:
                        r2[j + 1] = 1 + a1
        aux = r1
        r1, r2 = r2, aux
    return r1[-1]
