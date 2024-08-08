import re
from typing import Optional

NOUN_ENDINGS_DE = re.compile(
    r"(?:erei|heit|keit|ion|schaft|tät|[^jlz]ung)(en)?$|"
    r"(?:euse|icen|logie)(n)?$|"
    r"(?:bold|[^hkl]ling|ment)(e?[ns]?)?$|"
    r"(?:ikus)(sen?)?$|"
    r"(?:erl|iker|[^e]iter)([ns])?$|"
    r"(?:gramm|[^ä]nom)(e?s|en)?$|"
    r"(?:eur)(en?|s)?$|"
    r"(?:ar|lein|stan|um)(s)?$",
    re.I,
)


ADJ_ENDINGS_DE = re.compile(
    r"^(.{4,})"
    r"(artig|esk|oid|op|phil|phob|selig|schig)"
    r"(?:er|e?st)?(?:e|em|en|er|es)?$"
)

PLUR_ORTH_DE = re.compile(r"(?:Innen|\*innen|\*Innen|-innen|_innen)$")

PP_DE = re.compile(r"^(.{2,}ge.+?[^aes]t)(?:e|em|er|es)$")

ENDING_CHARS_DE = {"e", "m", "n", "r", "s"}


def apply_de(token: str) -> Optional[str]:
    "Apply pre-defined rules for German."
    if len(token) < 7:
        return None

    # nouns
    if token[0].isupper():
        # noun endings/suffixes: regex search
        if match := NOUN_ENDINGS_DE.search(token):
            # apply pattern
            ending = next((g for g in match.groups() if g), None)
            return token[: -len(ending)] if ending else token
        # inclusive speech
        # Binnen-I: ArbeitnehmerInnenschutzgesetz?
        if PLUR_ORTH_DE.search(token):
            return PLUR_ORTH_DE.sub(":innen", token)

    # mostly adjectives and verbs
    elif token[-1] in ENDING_CHARS_DE:
        if adj_match := ADJ_ENDINGS_DE.match(token):
            return (adj_match[1] + adj_match[2]).lower()
        if pp_match := PP_DE.match(token):
            return pp_match[1].lower()

    return None
