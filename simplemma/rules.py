"""Simple rules for unknown tokens."""

import re

from typing import Optional


RULES_LANGS = {"de", "en"}

ADJ_DE = re.compile(
    r"^(.+?)(arm|artig|bar|chig|ell|en|end|erig|ern|fach|frei|haft|iert|igt|isch|iv|lich|los|mäßig|reich|rig|sam|sch|schig|voll)(?:er|e?st)?(?:e|em|en|er|es)?$"
)  # ig
# https://de.wiktionary.org/wiki/-ent

NOUN_ENDINGS_DE = re.compile(
    r"(?:and|ant|ent|erei|erie|heit|ik|ist|keit|or|schaft|tät|tion|ung|ur)en$|(?:eur|ich|ier|ling|ör)e$"
)  # ig
PLUR_ORTH_DE = re.compile(r"Innen|\*innen|\*Innen|-innen|_innen")

GENITIVE_DE = re.compile(
    "(?:aner|chen|ent|eur|ier|iker|ikum|iment|iner|iter|ium|land|lein|ler|ling|ner|tum)s$"
)  # er
GERUNDIVE_DE = re.compile(r"end(?:e|em|en|er)$")
PP_DE = re.compile(r"ge.+?t(?:e|em|en|er|es)$")
COMP_ADJ = re.compile(r"st(e|em|en|es|er)?$")

ENDING_CHARS_NN_DE = {"e", "m", "n", "r", "s"}
ENDING_CHARS_ADJ_DE = ENDING_CHARS_NN_DE.union({"d", "t"})
ENDING_DE = re.compile(r"(?:e|em|en|er|es)$")


def apply_rules(token: str, langcode: Optional[str]) -> Optional[str]:
    "Apply pre-defined rules for certain languages."
    candidate = None
    if langcode == "de":
        candidate = apply_de(token)
    elif langcode == "en":
        candidate = apply_en(token)
    return candidate


def apply_de(token: str) -> Optional[str]:
    "Apply pre-defined rules for German."
    if token[0].isupper() and len(token) > 8 and token[-1] in ENDING_CHARS_NN_DE:
        # plural noun forms
        match = NOUN_ENDINGS_DE.search(token)
        if match:
            # -en pattern
            if match[0].endswith("n"):
                return token[:-2]
            # -e pattern
            return token[:-1]
        # genitive – too rare?
        if token[-1] == "s" and GENITIVE_DE.search(token):
            return token[:-1]
        # -end
        if GERUNDIVE_DE.search(token):
            return ENDING_DE.sub("er", token)
        # plural
        if token.endswith("nnen"):
            # inclusive speech
            # + Binnen-I: ArbeitnehmerInnenschutzgesetz?
            if PLUR_ORTH_DE.search(token):
                return PLUR_ORTH_DE.sub(":innen", token)
            # normalize without regex
            return token[:-3]
    # adjectives
    elif token[0].islower():  # and token[-1] in ENDING_CHARS_ADJ_DE
        candidate, alternative = None, None
        # general search
        if ADJ_DE.match(token):
            candidate = ADJ_DE.sub(r"\1\2", token)
        # specific cases
        if token[-1] in ENDING_CHARS_ADJ_DE:
            if COMP_ADJ.search(token):
                alternative = COMP_ADJ.sub("", token)
            elif PP_DE.search(token):
                alternative = ENDING_DE.sub("", token)
        # summing up
        if alternative:
            if not candidate:
                return alternative
            if candidate and len(alternative) < len(candidate):
                return alternative
        return candidate
    return None


def apply_en(token: str) -> Optional[str]:
    "Apply pre-defined rules for English."
    # nouns
    if token[-1] == "s":
        if token.endswith("ies") and len(token) > 7:
            if token.endswith("cies"):
                return token[:-4] + "cy"
            if token.endswith("ries"):
                return token[:-4] + "ry"
            if token.endswith("ties"):
                return token[:-4] + "ty"
        if token.endswith("doms"):
            return token[:-4] + "dom"
        if token.endswith("esses"):
            return token[:-5] + "ess"
        if token.endswith("isms"):
            return token[:-4] + "ism"
        if token.endswith("ists"):
            return token[:-4] + "ist"
        if token.endswith("ments"):
            return token[:-5] + "ment"
        if token.endswith("nces"):
            return token[:-4] + "nce"
        if token.endswith("ships"):
            return token[:-5] + "ship"
        if token.endswith("tions"):
            return token[:-5] + "tion"
    # verbs
    elif token.endswith("ed"):
        if token.endswith("ated"):
            return token[:-4] + "ate"
        if token.endswith("ened"):
            return token[:-4] + "en"
        if token.endswith("fied"):
            return token[:-4] + "fy"
        if token.endswith("ized"):
            return token[:-4] + "ize"
    return None
