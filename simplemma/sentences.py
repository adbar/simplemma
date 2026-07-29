"""Sentence splitting: `split_sentences()` segments raw text into sentences."""

import re
from collections.abc import Iterator

from .utils import normalize_token, validate_lang_input

# el: ';' is the question mark, U+037E its legacy spelling
_TERMINATORS = {None: ".!?…։؟।॥", "el": ".!?…;\u037e"}
# a lowercase word may still open a sentence after these (el question mark too)
_STRONG_TERMINATORS = "?!;\u037e"
_CLOSERS = "\"'”’»)]"
_EDGE = "(["  # stripped for the abbreviation lookup only; not quotes
_EMPTY: frozenset[str] = frozenset()
_PARAGRAPH = re.compile(r"\n\s*\n")
_WORD = re.compile(r"\S+")

# Only languages where the list measurably pays carry one.
_ABBREVS = {
    "cs": frozenset("dr judr prof".split()),
    "de": frozenset("bzw ca dr fr hr prof st u.a z.b".split()),
    "en": frozenset(
        "a.m col corp d.c dec dr e.g gen inc jan jr lt mr mrs ms n.j p.s sept st "
        "u.n u.s vs".split()
    ),
    "fr": frozenset("av cf dr mm st".split()),
    "nl": frozenset("dr drs ds int ir j.w m.g mgr mr nr o.a st th v.d".split()),
    "pl": frozenset(
        "art gen godz kpt m.in np ok pn pocz prof rys str tzw ul ur św".split()
    ),
    "pt": frozenset("av dr ed fund j.b j.j mr p.j pág sr sra t.j tel".split()),
}

_STARTERS = {
    "cs": frozenset(
        "ale bohužel dnes dokud hlavní jak jde jelikož jenže jestliže já kdyby "
        "když kromě musíme my myslím navíc oba po podle pokud praha proto přesto "
        "přitom snad ta tato ten tento ti to toto v vyplývá vždyť zatímco zdá "
        "zároveň".split()
    ),
    "de": frozenset(
        "aber abgesehen allerdings am anders auch bei beide da dabei dafür damit "
        "danach daneben daraus darin darüber das dass davon dazu denn dennoch der "
        "deshalb die dies diese dieser dieses doch ebenso ein eine entscheidend "
        "er es ferner ganz gerade hier hingegen hinzu im in insbesondere "
        "inzwischen letztere man mit nach nachdem natürlich neben nun ob obwohl "
        "seit selbst selbstverständlich sie so solche sonst statt trotz trotzdem "
        "umgekehrt unter vielmehr warum was wenn wer wie wir wo während zudem "
        "zwar zweitens".split()
    ),
    "fr": frozenset(
        "a ainsi alors après c car ce cela cependant certains certes ces cet "
        "cette comment dans depuis dès elle elles en enfin il ils je l la le les "
        "mais malgré mr nous né on or pour pourtant puis quand quant selon si "
        "tout un une voilà".split()
    ),
    "nl": frozenset(
        "alleen als behalve bovendien daar daarbij daardoor daarmee daarna "
        "daarnaast daarom dat de dit er het hij hoewel ik in maar na naast nee "
        "ook pas tijdens toen vandaar verder volgens vooral waarom want wat we "
        "wie wij ze zij zo".split()
    ),
    "pt": frozenset(
        "a afinal agora aliás além apesar as assim colaborou daí depois ela elas "
        "ele eles embora erramos essa essas esse esses este eu fhc folha há isso "
        "mas na no não o os outra outro quando quem segundo talvez é".split()
    ),
}

_JUNCTIONS = {
    lang: re.compile(f"[{re.escape(terms)}][{re.escape(_CLOSERS)}]*\\s+")
    for lang, terms in _TERMINATORS.items()
}

# longer than any suppressible core, so no rule can apply past it
_WINDOW = 1 + max(len(entry) for entries in _ABBREVS.values() for entry in entries)


def _dot_verdict(
    text: str,
    start: int,
    pos: int,
    terminators: str,
    abbrevs: frozenset[str],
) -> bool | None:
    """True suppresses the boundary (the default), False opens it, None rules
    the junction out entirely."""
    if pos <= start or text[pos - 1].isspace():
        return True
    if pos - _WINDOW >= start and text[pos - _WINDOW : pos].isalpha():
        return False
    i = pos - 1
    while i >= start and not text[i].isspace():
        i -= 1
    i += 1
    raw = text[i:pos]
    word = raw.strip(_EDGE)
    core = normalize_token(word.lower()).rstrip(terminators)
    if not core:
        # a bare run of one terminator ends a sentence ('...'), but a mixed run
        # does not, and a bracketed one is an in-sentence elision ('(...)')
        return not (word and word == raw == text[pos] * len(word))
    if len(core) == 1 and core.isalpha():
        if word[:1].isupper():
            return None  # initial before a starter is a name
        return not (i > 1 and text[i - 2].isdigit())  # digit-unit, e.g. '3 m.'
    if core.isdigit() and len(core) <= 2:
        return True  # ordinal
    return core in abbrevs


def _starter_follows(text: str, after: int, starters: frozenset[str]) -> bool:
    """Does a known sentence starter follow, overriding a suppressed '.'?"""
    if not starters:
        return False
    nxt_word = _WORD.match(text, after, after + 30)
    return (
        nxt_word is not None and normalize_token(nxt_word.group().lower()) in starters
    )


def _profile(
    code: str,
) -> tuple[str, "re.Pattern[str]", frozenset[str], frozenset[str]]:
    """Terminators, junction pattern, abbreviations and starters for `code`."""
    key = code if code in _TERMINATORS else None
    return (
        _TERMINATORS[key],
        _JUNCTIONS[key],
        _ABBREVS.get(code, _EMPTY),
        _STARTERS.get(code, _EMPTY),
    )


def _split_block(
    text: str,
    junction: "re.Pattern[str]",
    terminators: str,
    abbrevs: frozenset[str],
    starters: frozenset[str],
) -> Iterator[str]:
    start = 0
    for match in junction.finditer(text):
        pos, after = match.span()
        term = text[pos]
        if term == ".":
            verdict = _dot_verdict(text, start, pos, terminators, abbrevs)
            if verdict is None:
                continue
            if verdict and not _starter_follows(text, after, starters):
                continue
        if text[after : after + 1].islower() and not (
            term in _STRONG_TERMINATORS and text[pos + 1].isspace()
        ):
            continue
        yield text[start:after].strip()
        start = after
    tail = text[start:].strip()
    if tail:
        yield tail


def _blocks(text: str) -> Iterator[str]:
    """Blank-line-separated blocks, one at a time."""
    start = 0
    for gap in _PARAGRAPH.finditer(text):
        yield text[start : gap.start()]
        start = gap.end()
    yield text[start:]


def split_sentences(text: str, lang: str | tuple[str, ...] | None = None) -> list[str]:
    """Split `text` into sentences (stripped slices of the input).

    Args:
        text (str): The text to segment.
        lang (str | tuple[str, ...] | None): Language code, e.g. "de", or a
            tuple as the other entry points take it. Defaults to None
            (generic rules).

    Returns:
        list[str]: The sentences, in order, without surrounding whitespace.
    """
    code = validate_lang_input(lang)[0] if lang is not None else ""
    terminators, junction, abbrevs, starters = _profile(code)
    return [
        sentence
        for block in _blocks(text)
        for sentence in _split_block(block, junction, terminators, abbrevs, starters)
    ]
