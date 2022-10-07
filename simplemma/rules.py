"""Simple rules for unknown tokens."""

import re

from typing import Optional


RULES_LANGS = {"de", "en", "fi"}

ADJ_DE = re.compile(
    r"^(.+?)(arm|artig|bar|chig|ell|en|end|erig|ern|esk|fach|fähig|förmig|frei|haft|iert|igt|isch|iv|lich|los|mäßig|reich|rig|sam|sch|schig|selig|voll)(?:er|e?st)?(?:e|em|en|er|es)?$"
)

NOUN_ENDINGS_DE = re.compile(
    r"(?:and|ant|anz|ent|enz|erei|erie|heit|ik|ion|ist|keit|nom|or|schaft|tät|tion|ung|ur)(en)?$|"
    r"(?:eur|ich|ier|ling|om|ör|nis)(en?)?$|"
    r"(?:ette)(n)?$|"  # ie|er
    r"(?:chen|ent|erl|eur|gramm|iker|iter|land|lein|ler|ling|loge|ment|ner|om|stan|thek|um)(e?s)?$"  # en|er
)

PLUR_ORTH_DE = re.compile(r"Innen|\*innen|\*Innen|-innen|_innen")
GERUNDIVE_DE = re.compile(r"end(?:e|em|en|er)$")
PP_DE = re.compile(r"ge.+?t(?:e|em|en|er|es)$")
COMP_ADJ = re.compile(r"st(e|em|en|es|er)?$")

ENDING_CHARS_NN_DE = {"e", "m", "n", "r", "s"}
ENDING_CHARS_ADJ_DE = ENDING_CHARS_NN_DE.union({"d", "t"})
ENDING_DE = re.compile(r"(?:e|em|en|er|es)$")

SUFFIX_RULES_FI = {
    "isille": "inen",
    "isiksi": "inen",
    "isemme": "inen",
    "iseksi": "inen",
    "iselle": "inen",
    "isenne": "inen",
    "isten": "inen",
    "iseen": "inen",
    "isien": "inen",
    "iseni": "inen",
    "isesi": "inen",
    "inne": "i",
    "insa": "i",
    "isen": "inen",
    "iset": "inen",
    "ini": "i",
    "ain": "a",
    "eja": "i",
}
SUFFIX_RULES_FI_LENGTHS = sorted(
    {len(suffix) for suffix in SUFFIX_RULES_FI}, reverse=True
)


def apply_rules(
    token: str, langcode: Optional[str], greedy: bool = False
) -> Optional[str]:
    "Apply pre-defined rules for certain languages."
    candidate = None
    if langcode == "de":
        candidate = apply_de(token, greedy)
    elif langcode == "en":
        candidate = apply_en(token)
    elif langcode == "fi":
        candidate = apply_fi(token)
    return candidate


def apply_de(token: str, greedy: bool = False) -> Optional[str]:
    "Apply pre-defined rules for German."
    if token[0].isupper() and len(token) > 7 and token[-1] in ENDING_CHARS_NN_DE:
        # bypass
        if token.endswith("er"):
            return token
        # plural noun forms
        match = NOUN_ENDINGS_DE.search(token)
        if match and len(match[0]) > 2:
            groups = [g for g in match.groups() if g is not None]
            # lemma identified
            return token[: -len(groups[0])] if groups else token
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
            # last resort
            # if greedy:
            # -s → ø
            # if token[-1] == "s":
            #    return token[:-1]
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
            # last resort
            if not alternative and greedy:
                if token[-4:-2] == "ig":
                    alternative = token[:-2]
                elif token[-3:-1] == "ig":
                    alternative = token[:-1]
        # summing up
        if alternative:
            if not candidate:
                return alternative
            if len(alternative) < len(candidate):
                return alternative
        return candidate
    return None


def apply_en(token: str) -> Optional[str]:
    "Apply pre-defined rules for English."
    # nouns
    if token[-1] == "s":
        if token.endswith("ies") and len(token) > 7:
            if token.endswith("cies"):
                return f"{token[:-4]}cy"
            if token.endswith("ries"):
                return f"{token[:-4]}ry"
            if token.endswith("ties"):
                return f"{token[:-4]}ty"
        if token.endswith("doms"):
            return f"{token[:-4]}dom"
        if token.endswith("esses"):
            return f"{token[:-5]}ess"
        if token.endswith("isms"):
            return f"{token[:-4]}ism"
        if token.endswith("ists"):
            return f"{token[:-4]}ist"
        if token.endswith("ments"):
            return f"{token[:-5]}ment"
        if token.endswith("nces"):
            return f"{token[:-4]}nce"
        if token.endswith("ships"):
            return f"{token[:-5]}ship"
        if token.endswith("tions"):
            return f"{token[:-5]}tion"
    elif token.endswith("ed"):
        if token.endswith("ated"):
            return f"{token[:-4]}ate"
        if token.endswith("ened"):
            return f"{token[:-4]}en"
        if token.endswith("fied"):
            return f"{token[:-4]}fy"
        if token.endswith("ized"):
            return f"{token[:-4]}ize"
    return None


def apply_fi(token: str) -> Optional[str]:
    "Apply pre-defined rules for Finnish."
    for length in SUFFIX_RULES_FI_LENGTHS:
        if len(token) < length + 2:
            continue  # token is too short to try suffix rules
        suffix = token[-length:]
        if suffix in SUFFIX_RULES_FI:
            return token[:-length] + SUFFIX_RULES_FI[suffix]
    return None
