"""
This file defines the `ApostropheBoundaryStrategy` class, which handles
languages whose orthography marks a fixed morpheme boundary with an
apostrophe (Turkish: proper-noun/suffix boundary, e.g. "Istanbul'da").
Unlike a clitic table, this is unconditional for the language: everything
after the first apostrophe is a suffix, and the head is looked up via the
REST of the pipeline (proper nouns are their own lemma; common nouns may
still need rule/affix processing on the head alone).
"""

from collections.abc import Callable

from .lemmatization_strategy import LemmatizationStrategy

# UD-validated (training/data/affix_eval/, tr_imst -- see
# training/data/affix_eval/README.md "Apostrophe/proclitic elision").
# Plain dictionary lookup only resolves ~12% of gold apostrophe forms
# (the dictionary's apostrophe-bearing entries are common combinations;
# proper nouns are open-class, no fixed table can cover them) -- the
# orthographic rule generalizes where a lookup table can't.
APOSTROPHE_BOUNDARY_LANGS = frozenset({"tr"})
MIN_HEAD_LEN = 2


def _case_key(word: str) -> str:
    return word.lower().replace("i̇", "i")


class ApostropheBoundaryStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy for languages where an apostrophe marks a
    fixed morpheme boundary: splits at the first apostrophe and
    lemmatizes the head via the rest of the pipeline.
    """

    __slots__ = ["_lemmatize_head"]

    def __init__(self, lemmatize_head: Callable[[str, str], str | None]):
        """
        Initialize the Apostrophe Boundary Strategy.

        Args:
            lemmatize_head (Callable[[str, str], str | None]): Callback
                used to lemmatize the head (the part before the
                apostrophe) -- ordinarily the owning `DefaultStrategy`'s
                own `get_lemma`, so the head benefits from the full
                pipeline. Injected rather than composed to avoid a
                circular construction dependency.
        """
        self._lemmatize_head = lemmatize_head

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get the lemma of a token by splitting at the first apostrophe.

        Args:
            token (str): The input token.
            lang (str): The language code.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        if lang not in APOSTROPHE_BOUNDARY_LANGS:
            return None
        # Both apostrophe variants mark the boundary (smart quotes are
        # the default in most editors; NFC does not unify them).
        boundary = token.replace("’", "'").find("'")
        if boundary < MIN_HEAD_LEN or boundary == len(token) - 1:
            return None
        head = token[:boundary]
        lemma = self._lemmatize_head(head, lang)
        if lemma is None:
            return None
        # A case-only change (a proper noun the dictionary only has
        # under a different case) is an artifact of DictionaryLookupStrategy's
        # own case-fallback, not a real morphological answer -- the
        # apostrophe boundary is what's informative here, not the dict's
        # casing. Restore the original head's case in that situation.
        # (The dotted-I normalization covers Turkish's "İ".lower(),
        # which yields "i" + a combining dot, not a plain "i".)
        return head if _case_key(lemma) == _case_key(head) else lemma
