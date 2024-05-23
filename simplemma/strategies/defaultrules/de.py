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
PP_DE = re.compile(r"^.{2,}ge.+?[^aes]t(?:e|em|er|es)$")

ENDING_CHARS_DE = {"e", "m", "n", "r", "s"}
ENDING_DE = re.compile(r"(?:e|em|er|es)$")


def apply_de(token: str) -> Optional[str]:
    "Apply pre-defined rules for German."
    if len(token) < 7:
        return None

    # nouns
    if token[0].isupper():
        # noun endings/suffixes: regex search
        match = NOUN_ENDINGS_DE.search(token)
        if match:
            # apply pattern
            ending = next((g for g in match.groups() if g is not None), None)
            if ending:
                return token[: -len(ending)]
            # lemma identified
            return token
        # inclusive speech
        # Binnen-I: ArbeitnehmerInnenschutzgesetz?
        if PLUR_ORTH_DE.search(token):
            return PLUR_ORTH_DE.sub(":innen", token)

    # mostly adjectives and verbs
    elif token[-1] in ENDING_CHARS_DE:
        if ADJ_ENDINGS_DE.match(token):
            return ADJ_ENDINGS_DE.sub(r"\1\2", token).lower()
        if PP_DE.search(token):
            return ENDING_DE.sub("", token).lower()

    return None
