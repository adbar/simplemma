"""
Sentence-initial casing and ALL-CAPS acronym heuristics for full-text
lemmatization (GH#93). Two per-language policies keyed on the first language:
sentence-initial lowering (gated for GATED_INITIAL_LOWERING_LANGS to spare
proper nouns) and ALL-CAPS acronym keeping (ALLCAPS_KEEP_LANGS). Both need a
dictionary-membership check; without one, only base initial-lowering applies.
"""

import re
from collections.abc import Callable, Iterator
from typing import Protocol, runtime_checkable

from .utils import normalize_token

# (token, lang) -> is it a literal dictionary key? (no case/apostrophe fallback)
MembershipCheck = Callable[[str, str], bool]


@runtime_checkable
class SupportsMembership(Protocol):
    """A lemmatization strategy exposing a raw dictionary-membership check (no
    case/apostrophe fallback), which the casing heuristics require."""

    def is_dictionary_member(self, token: str, lang: str) -> bool:
        """Whether `token` is a literal dictionary key for `lang`."""


# Sentence terminators only (narrower than the tokenizer's punctuation class).
PUNCTUATION = frozenset({".", "?", "!", "…", "¿", "¡", "։"})  # ։ = Armenian full stop
GATED_INITIAL_LOWERING_LANGS = frozenset({"da", "de", "en"})
ALLCAPS_KEEP_LANGS = frozenset({"ca", "de", "es", "hy", "lt", "lv", "pt", "uk"})
SHOUTING_THRESHOLD = 0.5
SENTENCE_BUFFER_CAP = 512  # flush ceiling so punctuation-free input still streams

# 3+ char Roman numerals (XII, MCM) are numerals, not acronyms; 2-char CD/DC/MM
# stay keepable. Lookahead rejects the empty match the all-optional body accepts.
_ROMAN_NUMERAL = re.compile(
    r"(?=[MDCLXVI])M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
)


def is_sentence_boundary(token: str) -> bool:
    """Whether the next token starts a sentence (buffered path only). First
    char, so collapsed runs ('...') match; alnum-final tokens (".270") don't.
    The streaming path uses a stricter rule on purpose -- see `_streaming`."""
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
    """Makes the casing decisions for one request over a token stream; the
    caller lemmatizes. `member` is the raw dictionary membership check; None
    (strategy has no dictionary) disables the gated and acronym heuristics,
    leaving only base initial-lowering."""

    __slots__ = ("_lang0", "_member", "_gated", "_acronym")

    def __init__(self, lang0: str, member: MembershipCheck | None) -> None:
        self._lang0 = lang0
        self._member = member
        self._gated = member is not None and lang0 in GATED_INITIAL_LOWERING_LANGS
        self._acronym = member is not None and lang0 in ALLCAPS_KEEP_LANGS

    def apply(self, tokens: Iterator[str]) -> Iterator[tuple[str, bool]]:
        """Casing decisions for raw tokenizer `tokens`: (surface, keep) pairs
        where surface is NFC (safe to look up as-is) and keep means yield it
        verbatim as an acronym instead of lemmatizing. The acronym path buffers
        one sentence at a time (it needs the whole sentence's shouting ratio);
        the default path streams in constant memory."""
        nfc = (normalize_token(t) for t in tokens)  # NFC once: probes match dicts
        return self._buffered(nfc) if self._acronym else self._streaming(nfc)

    def initial_surface(self, token: str) -> str:
        """Surface form for a sentence-initial (NFC) token: lowered, unless a
        gated language flags it as a probable proper noun (kept as-is)."""
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
        """Yield this ALL-CAPS token verbatim instead of lemmatizing? Initial
        position also requires neither its Titlecase (e.g. BERLIN) nor
        lowercase form to be a dictionary entry, else the D' gate runs."""
        if shouting or not is_keepable_allcaps(token):
            return False
        if not initial:
            return True
        assert self._member is not None  # only reached on the acronym path
        return not self._member(token.capitalize(), self._lang0) and not self._member(
            token.lower(), self._lang0
        )
