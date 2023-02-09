import re

from typing import Optional


NOUN_ENDINGS_DE = re.compile(
    r"(?:bold|[^kl]ling|ment)(e?[ns]?)?$|"
    r"ikus(sen?)?$|"
    r"(?:erl|iker|[^e]iter)([ns])?$|"
    r"(?:gramm|nom)(e?s|en)?$|"
    r"(?:eur)(en?|s)?$|"
    r"(?:ar|er|lein|o|stan|um)(s)?$"
)

ADJ_ENDINGS_DE = re.compile(
    r"^(.{4,}?)(?<!zu)"
    r"(arm|artig|bar|chig|[^i]ent|erig|esk|fähig|förmig|frei|[^c]haft|iv|[^fh]los|mäßig|oid|op|phil|phob|sam|schig|selig|voll)"  # [^b]rig|
    r"(?:er|e?st)?(?:e|em|en|er|es)$"
)

PLUR_ORTH_DE = re.compile(r"(?:Innen|\*innen|\*Innen|-innen|_innen)$")
GERUND_DE = re.compile(r"([elr]nd)(?:e|em|en|er)$")
GERUNDIVE_DE = re.compile(r"([elr]nd)(?:st)?(?:e|em|en|er|es)$")
PP_DE = re.compile(r"^.{2,}ge.+?[^aes]t(?:e|em|er|es)$")  # en|

ENDING_CHARS_NN_DE = {"e", "m", "n", "r", "s"}
ENDING_CHARS_ADJ_DE = ENDING_CHARS_NN_DE.union({"d", "t"})
ENDING_DE = re.compile(r"(?:e|em|en|er|es)$")

# 2-letter prefixes are theoretically already accounted for by the current AFFIXLEN parameter
GERMAN_PREFIXES = {
    "ab",
    "an",
    "auf",
    "aus",
    "be",
    "bei",
    "da",
    "dar",
    "durch",
    "ein",
    "ent",
    "er",
    "gegen",
    "her",
    "heran",
    "herab",
    "herauf",
    "heraus",
    "herein",
    "herum",
    "herunter",
    "hervor",
    "hin",
    "hinauf",
    "hinaus",
    "hinein",
    "hinter",
    "hinunter",
    "hinweg",
    "hinzu",
    "los",
    "miss",
    "mit",
    "nach",
    "neben",
    "ran",
    "raus",
    "rein",
    "rum",
    "runter",
    "über",
    "unter",
    "ver",
    "vor",
    "voran",
    "voraus",
    "vorbei",
    "vorher",
    "vorüber",
    "weg",
    "weiter",
    "wieder",
    "zer",
}


def fix_known_prefix_de(token: str):
    prefix = next((p for p in GERMAN_PREFIXES if token.startswith(p)), None)
    if prefix is None or token[len(prefix) : len(prefix) + 2] == "zu":
        return None

    return prefix


def apply_de(token: str, greedy: bool = False) -> Optional[str]:
    "Apply pre-defined rules for German."
    if len(token) < 7:
        return None
    # nouns
    if token[0].isupper():  # and token.endswith("en"):
        if token.endswith(("ereien", "heiten", "keiten", "ionen", "schaften", "täten")):
            return token[:-2]
        if token.endswith(("eusen", "icen", "logien")):
            return token[:-1]
        if token.endswith("ungen") and not (
            "jungen" in token or "lungen" in token or "zungen" in token
        ):
            return token[:-2]
        # inclusive speech
        # + Binnen-I: ArbeitnehmerInnenschutzgesetz?
        if PLUR_ORTH_DE.search(token):
            return PLUR_ORTH_DE.sub(":innen", token)
        # noun endings/suffixes: regex search
        # series of noun endings
        match = NOUN_ENDINGS_DE.search(token)
        if match:
            # lemma identified
            if not match[1]:
                return token
            return token[:-len(match[1])]
        # -end and gerunds
        if greedy and GERUND_DE.search(token):
            return ENDING_DE.sub("e", token)
    # mostly adjectives and verbs
    elif greedy and token[-1] in ENDING_CHARS_ADJ_DE:
        # general search
        if ADJ_ENDINGS_DE.match(token):
            return ADJ_ENDINGS_DE.sub(r"\1\2", token)
        if PP_DE.search(token):
            return ENDING_DE.sub("", token)
        if GERUNDIVE_DE.search(token):  # -end and gerundives
            return GERUNDIVE_DE.sub(r"\1", token)
    return None
