"""Sentence-initial casing and ALL-CAPS acronym heuristics for full-text lemmatization.

Both policies are keyed on the first language and need a dictionary membership check.
"""

import re
import unicodedata
from collections.abc import Callable, Iterator


# (token, lang) -> is it a literal dictionary key, no case fallback
MembershipCheck = Callable[[str, str], bool]


PUNCTUATION = frozenset({".", "?", "!", "…", "¿", "¡", "։"})  # ։ = Armenian full stop
GATED_INITIAL_LOWERING_LANGS = frozenset({"da", "de", "en"})
ALLCAPS_KEEP_LANGS = frozenset({"ca", "de", "es", "hy", "lt", "lv", "pt", "uk"})
SHOUTING_THRESHOLD = 0.5
SENTENCE_BUFFER_CAP = 512  # flush ceiling so punctuation-free input still streams

# the lookahead rejects the empty match of the all-optional body
_ROMAN_NUMERAL = re.compile(
    r"(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
)


def is_sentence_boundary(token: str) -> bool:
    """Whether the next token starts a sentence, on the buffered path."""
    return token[:1] in PUNCTUATION and not token[-1:].isalnum()


def _after_initial(prev: str, token: str) -> bool:
    """Terminator following a single-letter token: 'J. Schmidt', no boundary."""
    return token[:1] == "." and len(prev) == 1 and prev.isalpha()


def is_keepable_allcaps(token: str) -> bool:
    """ALL-CAPS token worth keeping verbatim as a likely acronym."""
    return (
        len(token) >= 2
        and token.isalpha()
        and token.isupper()
        and not (len(token) >= 3 and _ROMAN_NUMERAL.fullmatch(token))
    )


class SentenceCasing:
    """Casing decisions over a token stream.

    With `member` set to None only plain sentence-initial lowering applies.
    """

    __slots__ = ("_lang0", "_member", "_gated", "_acronym")

    def __init__(self, lang0: str, member: MembershipCheck | None) -> None:
        self._lang0 = lang0
        self._member = member
        self._gated = member is not None and lang0 in GATED_INITIAL_LOWERING_LANGS
        self._acronym = member is not None and lang0 in ALLCAPS_KEEP_LANGS

    def apply(self, tokens: Iterator[str]) -> Iterator[tuple[str, bool]]:
        """Yield (NFC surface, keep verbatim as acronym) pairs for `tokens`."""
        nfc = (unicodedata.normalize("NFC", t) for t in tokens)
        return self._buffered(nfc) if self._acronym else self._streaming(nfc)

    def initial_surface(self, token: str) -> str:
        """Lowered sentence-initial token, unless gated as a probable proper noun."""
        lowered = token.lower()
        if not self._gated:
            return lowered
        assert self._member is not None  # gated implies a membership check
        if token.isupper() or self._member(lowered, self._lang0):
            return lowered
        return token

    def _streaming(self, tokens: Iterator[str]) -> Iterator[tuple[str, bool]]:
        initial = True
        prev = ""
        for token in tokens:
            yield (self.initial_surface(token) if initial else token, False)
            initial = token in PUNCTUATION and not _after_initial(prev, token)
            prev = token

    def _buffered(self, tokens: Iterator[str]) -> Iterator[tuple[str, bool]]:
        sentence: list[str] = []
        at_start = True
        prev = ""
        for token in tokens:
            sentence.append(token)
            boundary = is_sentence_boundary(token) and not _after_initial(prev, token)
            if boundary or len(sentence) >= SENTENCE_BUFFER_CAP:
                yield from self._emit(sentence, at_start)
                sentence = []
                at_start = boundary  # a capped flush leaves us mid-sentence
            prev = token
        if sentence:
            yield from self._emit(sentence, at_start)

    def _emit(self, tokens: list[str], at_start: bool) -> Iterator[tuple[str, bool]]:
        n_alpha = n_shout = 0
        for token in tokens:
            if token.isalpha():
                n_alpha += 1
                if len(token) >= 2 and token.isupper():  # counts Roman numerals too
                    n_shout += 1
        # leave-one-out: a candidate must not count itself as shouting
        shouting = n_alpha > 1 and (n_shout - 1) / (n_alpha - 1) >= SHOUTING_THRESHOLD
        initial = (
            next((i for i, t in enumerate(tokens) if t[:1].isalnum()), -1)
            if at_start
            else -1
        )
        for i, token in enumerate(tokens):
            if self._keep_as_acronym(token, i == initial, shouting):
                yield (token, True)
            else:
                yield (self.initial_surface(token) if i == initial else token, False)

    def _keep_as_acronym(self, token: str, initial: bool, shouting: bool) -> bool:
        """Whether to keep this ALL-CAPS token verbatim."""
        if shouting or not is_keepable_allcaps(token):
            return False
        if not initial:
            return True
        assert self._member is not None  # only reached on the acronym path
        return not self._member(token.capitalize(), self._lang0) and not self._member(
            token.lower(), self._lang0
        )
