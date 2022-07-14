"""Simple rules for unknown tokens."""

import re

from typing import Optional


ADJ_DE = re.compile(
    r"^(.+?)(arm|artig|bar|chig|ell|en|end|erig|ern|fach|frei|haft|iert|igt|isch|iv|lich|los|mäßig|reich|rig|sam|sch|schig|voll)(er|e?st)?(e|em|en|es|er)?$"
)  # ig
# https://de.wiktionary.org/wiki/-ent

ENDING_DE = re.compile(r"(e|em|en|er|es)$")


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
    if token[0].isupper() and len(token) > 8:
        if ENDING_DE.search(token):
            # plural noun forms
            if re.search(
                "(and|ant|ent|erei|erie|heit|ik|ist|keit|or|schaft|tät|tion|ung|ur)en$",
                token,
            ):
                return token[:-2]
            if re.search("(eur|ich|ier|ling|ör)e$", token):  # ig
                return token[:-1]
            # genitive – too rare?
            # if re.search('(aner|chen|eur|ier|iker|ikum|iment|iner|iter|ium|land|lein|ler|ling|ner|tum)s$', token):  # er
            #    return token[:-1]
            # -end
            if re.search("end(e|em|en|er)$", token):
                return ENDING_DE.sub("er", token)
        # inclusive speech
        # + Binnen-I: ArbeitnehmerInnenschutzgesetz?
        if token.endswith("nnen"):
            return re.sub(r"Innen|\*innen|\*Innen|-innen", ":innen", token)
    # adjectives
    elif token[0].islower():
        if ADJ_DE.match(token):
            return ADJ_DE.sub(r"\1\2", token)
        if re.search(r"ge.+?t(e|em|en|er|es)$", token):
            return ENDING_DE.sub("", token)
        # print(token)
        # if re.search(r'st(e|em|en|es|er)?$', token):
        #    return re.sub(r'st(e|em|en|es|er)?$', '', token)
    return None


def apply_en(token: str) -> Optional[str]:
    "Apply pre-defined rules for English."
    # nouns
    if token.endswith("s"):
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
    if token.endswith("ed"):
        if token.endswith("ated"):
            return token[:-4] + "ate"
        if token.endswith("ened"):
            return token[:-4] + "en"
        if token.endswith("fied"):
            return token[:-4] + "fy"
        if token.endswith("ized"):
            return token[:-4] + "ize"
    return None
