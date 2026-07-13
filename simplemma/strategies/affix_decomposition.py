"""
This file defines the `AffixDecompositionStrategy` class, which implements an affix decomposition lemmatization strategy in the Simplemma library.
"""

from .dictionary_lookup import DictionaryLookupStrategy

# Shared with GreedyDictionaryLookupStrategy's gate on purpose -- retuning
# it retunes both strategies.
from .greedy_dictionary_lookup import greedy_min_length
from .lemmatization_strategy import LemmatizationStrategy

# Membership and per-language values (max_affix_len) are UD-validated, not
# guesswork -- an in-dict-only measurement is not sufficient evidence to
# add or retune a language. See training/affixbuilder.py and
# training/download_eval_data.py; the UD gate under training/data/affix_eval/
# is local audit tooling (gitignored, not shipped -- rebuild it). Rejected despite looking positive
# in-dict: pt, ca, nl, en, la, gl, fr, it, ro (marginal), de
# (confirmed harmful on de_hdt too, not just a de_gsd artifact:
# inflected-adjective lemma convention + proper-noun mangling). is is
# positive but held for a future rules-file carve-out. es was rejected
# on UD v2.12 data, then accepted on v2.18: the old harm score was
# inflated by es_gsd's since-fixed PROPN-lowercasing convention
# (re-validated on es_gsd AND es_ancora, both modes, clean audits).
AFFIX_LANGS = {
    "bg": 2,
    "cs": 2,
    "da": 2,
    "el": 2,
    "es": 2,
    "et": 3,
    "fi": 5,
    "hu": 5,
    "hy": 2,
    "lt": 5,
    "lv": 2,
    "nb": 2,
    "nn": 2,
    "pl": 2,
    "ru": 2,
    "sk": 2,
    "tr": 5,
    "uk": 2,
}

# Languages excluded from greedy-mode decomposition: UD-measured harmful
# (ca/en/gl/it/la/nl/pt), a measured wash (id), or typologically wrong
# for a suffix-stripping algorithm (ms/sw/tl -- prefixing/mutating).
# Non-greedy mode never reaches them (non-members). it: added once
# CliticDecompositionStrategy claimed its main OOV class (verb+enclitic);
# unclaimed affix decomposition was over-firing on nominal suffixes
# (-ità/-ismo) and proper nouns (Afghanistan -> afghanistare).
# es was removed from this list after the v2.18 re-validation cleared
# it for both modes (see AFFIX_LANGS note above).
GREEDY_EXCLUDE = {
    "ca",
    "en",
    "gl",
    "id",
    "it",
    "la",
    "ms",
    "nl",
    "pt",
    "sw",
    "tl",
}

AFFIXLEN = 2  # max_affix_len for languages without an AFFIX_LANGS entry (greedy mode)
MINCOMPLEN = 4
# Decomposition is ~O(len²); cap long tokens (longest real form is 86 chars).
MAXLEN = 100


class AffixDecompositionStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy that uses affix decomposition to find lemmas of tokens.

    This strategy decomposes tokens into affixes and looks up their lemmas in a dictionary.
    It first attempts to decompose the token using affix decomposition and then falls back
    to suffix decomposition if affix decomposition fails.
    """

    __slots__ = ["_greedy", "_dictionary_lookup"]

    def __init__(
        self,
        greedy: bool,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        """
        Initialize the Affix Decomposition Strategy.

        Args:
            greedy (bool): Flag indicating whether to use greedy decomposition.
            dictionary_lookup (DictionaryLookupStrategy): The dictionary lookup strategy to use.
                Defaults to `DictionaryLookupStrategy()`.
        """
        self._greedy = greedy
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get the lemma of a token using affix decomposition strategy.

        Args:
            token (str): The input token.
            lang (str): The language code.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        excluded = lang in GREEDY_EXCLUDE if self._greedy else lang not in AFFIX_LANGS
        if excluded or len(token) <= greedy_min_length(lang) or len(token) > MAXLEN:
            return None

        # define parameters
        max_affix_len = AFFIX_LANGS.get(lang, AFFIXLEN)
        return self._affix_decomposition(
            token, lang, max_affix_len, MINCOMPLEN
        ) or self._suffix_decomposition(token, lang, MINCOMPLEN)

    def _affix_decomposition(
        self,
        token: str,
        lang: str,
        max_affix_len: int = 0,
        min_complem_len: int = 0,
    ) -> str | None:
        """
        Perform affix decomposition on a token.

        Args:
            token (str): The input token.
            lang (str): The language code.
            max_affix_len (int): The maximum length of the affix.
            min_complem_len (int): The minimum length of the complementary part.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        # Left-to-right languages only. A single pass at the largest affix
        # length is equivalent to looping over smaller ones (first match wins).
        for count in range(1, len(token) - min_complem_len + 1):
            part1 = token[:-count]
            lempart1 = self._dictionary_lookup.get_lemma(part1, lang)
            if lempart1 is None:
                continue
            # maybe an affix? discard it
            if count <= max_affix_len:
                return lempart1
            # account for case before looking for second part
            part2 = token[-count:]
            if token[0].isupper():
                part2 = part2.capitalize()
            lempart2 = self._dictionary_lookup.get_lemma(part2, lang)
            if lempart2 is None:
                continue
            # accept the dictionary form if not longer than the affix bound
            if len(lempart2) < len(part2) + max_affix_len:
                return part1 + lempart2.lower()
        return None

    def _suffix_decomposition(
        self,
        token: str,
        lang: str,
        min_complem_len: int = 0,
    ) -> str | None:
        """
        Decomposes the token using suffix decomposition strategy.

        Args:
            token (str): The token to be decomposed.
            lang (str): The language of the token.
            min_complem_len (int, optional): The minimum length of the complementary part
                to consider during decomposition. Defaults to 0.

        Returns:
            str | None: The decomposed token if decomposition is successful, None otherwise.
        """
        for count in range(len(token) - min_complem_len, min_complem_len - 1, -1):
            suffix = self._dictionary_lookup.get_lemma(
                token[-count:].capitalize(), lang
            )
            if suffix is not None and len(suffix) <= count:
                return token[:-count] + suffix.lower()

        return None
