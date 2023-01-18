"""Simple rules for unknown tokens."""

import re

from typing import Optional


RULES_LANGS = {"de", "en", "fi", "nl", "pl", "ru"}

# VOWELS = {"a", "e", "i", "o", "u", "y"}


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
    elif langcode == "nl":
        candidate = apply_nl(token)
    elif langcode == "pl":
        candidate = apply_pl(token)
    elif langcode == "ru":
        candidate = apply_ru(token)
    return candidate


NOUN_ENDINGS_DE = re.compile(
    r"(?:bold|[^kl]ling|ment)(e?[ns]?)?$|"
    r"(?:ikus)(sen?)?$|"
    r"(?:erl|iker|[^e]iter)([ns])?$|"
    r"(?:gramm|nom)(e?s|en)?$|"
    r"(?:eur)(en?|s)?$|"
    r"(?:ar|er|lein|o|stan|um)(s)?$"
)

ADJ_ENDINGS_DE = re.compile(
    r"^(.{4,}?)"
    r"(arm|artig|bar|chig|[^i]ent|erig|esk|fähig|förmig|frei|[^c]haft|iv|[^fh]los|mäßig|oid|op|phil|phob|[^b]rig|sam|schig|selig|voll)"
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
        # greedy search
        if greedy:
            # series of noun endings
            match = NOUN_ENDINGS_DE.search(token)
            if match and len(match[0]) > 2:
                groups = [g for g in match.groups() if g is not None]
                # lemma identified
                if not groups:
                    return token
                # apply -en/-e/-n/-s patterns
                return token[: -len(groups[0])]
            # -end and gerunds
            if GERUND_DE.search(token):
                return ENDING_DE.sub("e", token)
    # mostly adjectives and verbs
    elif token[-1] in ENDING_CHARS_ADJ_DE and greedy:
        # general search
        if ADJ_ENDINGS_DE.match(token):
            return ADJ_ENDINGS_DE.sub(r"\1\2", token)
        if PP_DE.search(token):
            return ENDING_DE.sub("", token)
        if GERUNDIVE_DE.search(token):  # -end and gerundives
            return GERUNDIVE_DE.sub(r"\1", token)
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
        if token.endswith("quies"):
            return token[:-3] + "y"
        if token.endswith("ships"):
            return token[:-5] + "ship"
        if token.endswith("tions"):
            return token[:-5] + "tion"
        if token.endswith("trices"):
            return token[:-3] + "x"
        if token.endswith("ums"):
            return token[:-1]
        # too much noise
        # if token.endswith("ae"):  # or token.endswith("as")
        #    return token[:-1]
        # if token.endswith("oes"):
        #    return token[:-2]
        # Pattern rules
        # if token.endswith("ies") and len(token) > 3 and token[-4] not in VOWELS:
        #    return token[:-3] + "y"  # complies => comply
        # if token.endswith(("sses", "shes", "ches", "xes")):
        #    return token[:-2]  # kisses => kiss
        # if token.endswith("erves"):
        #    return token[:-1]
        # if token.endswith("arves"):
        #    return token[:-3] + "f"

    # verbs
    # elif token.endswith("ed"):
    #    if token.endswith("ated"):
    #        return token[:-4] + "ate"
    #    if token.endswith("ened"):
    #        return token[:-4] + "en"
    #    if token.endswith("fied"):
    #        return token[:-4] + "fy"
    #    if token.endswith("ized"):
    #        return token[:-4] + "ize"
    #    # Pattern rules
    #    if token.endswith("ied"):
    #        return token[:-3] + "y"  # envied => envy
    #    # -ed could be added
    return None


def apply_nl(token: str) -> Optional[str]:
    "Apply pre-defined rules for Dutch."
    # inspired by:
    # https://github.com/clips/pattern/blob/master/pattern/text/nl/inflect.py
    # nouns
    if len(token) > 6:
        # achterpagina's => achterpagina
        if token.endswith("'s"):
            return token[:-2]
        # mogelijkheden => mogelijkheid
        if token.endswith("heden") and not "scheden" in token:
            return token[:-5] + "heid"
        # boerderijen => boerderij
        if token.endswith("ijen"):
            return token[:-2]
        # brieven => brief
        if token.endswith("ieven"):
            return token[:-3] + "f"
        # too much noise:
        # bacteriën => bacterie
        # if token.endswith("iën"):
        #    return token[:-2] + "e"
        # flessen => fles
        # if token.endswith("essen"):
        #    return token[:-3]
        # chinezen => chinees
        # if token.endswith("ezen") and token[-5] not in VOWELS:
        #    return token[:-4] + "ees"
        # if token.endswith("bele"):
        #    return token[:-1]
    return None


FINNISH_ENDINGS = {
    # -minen nouns, ä/ö/y + a/o/u
    # https://en.wiktionary.org/wiki/-minen
    "miset": "minen",
    "misen": "minen",
    "misten": "minen",
    "miseen": "minen",
    "misia": "minen",
    "misiä": "minen",
    "misiin": "minen",
    "misin": "minen",
    # -inen nouns
    "isissa": "inen",  # liikenaisissa → liikenainen
    "isissä": "inen",
    "isista": "inen",  # liikenaisista → liikenainen
    "isistä": "inen",
    "iseksi": "inen",  # liikenaiseksi → liikenainen
    "iseen": "inen",  # liikenaiseen → liikenainen
    "isella": "inen",  # liikenaisella → liikenainen
    "isellä": "inen",
    "iselle": "inen",  # liikenaiselle → liikenainen
    "iselta": "inen",  # liikenaiselta → liikenainen
    "iseltä": "inen",
    "iseni": "inen",  # liikenaiseni → liikenainen
    "isensa": "inen",  # liikenaisensa → liikenainen
    "isensä": "inen",
    "isesi": "inen",  # liikenaisesi → liikenainen
    "isessa": "inen",  # liikenaisessa → liikenainen
    "isessä": "inen",
    "isesta": "inen",  # liikenaisesta → liikenainen
    "isestä": "inen",
    "isien": "inen",  # liikenaisien → liikenainen
    "isiksi": "inen",  # liikenaisiksi → liikenainen
    "isilla": "inen",  # liikenaisilla → liikenainen
    "isillä": "inen",
    "isilta": "inen",  # liikenaisilta → liikenainen
    "isiltä": "inen",
    "isille": "inen",  # liikenaisille → liikenainen
    "isina": "inen",  # liikenaisina → liikenainen
    "isinä": "inen",
    "isineen": "inen",  # liikenaisineen → liikenainen
    "isitta": "inen",  # liikenaisitta → liikenainen
    "isittä": "inen",
    "isemme": "inen",  # liikenaisemme → liikenainen
    "isenne": "inen",  # liikenaisenne → liikenainen
    "isille": "inen",  # liikenaisille → liikenainen
    "iselta": "inen",  # liikenaiselta → liikenainen
    "iseltä": "inen",
    "isetta": "inen",  # liikenaisetta → liikenainen
    "isettä": "inen",
    # -ainen for more precision
    "aisen": "ainen",  # liikenaisen → liikenainen
    "aiset": "ainen",  # liikenaiset → liikenainen
    "aisia": "ainen",  # liikenaisia → liikenainen
    # -uus nouns: https://en.wiktionary.org/wiki/nerokkuus
    "uudet": "uus",
    "uuden": "uus",
    "uuksien": "uus",
    "uuksiin": "uus",
    "uuksia": "uus",
    "uudessa": "uus",
    "uuksissa": "uus",
    "uuteen": "uus",
    "uudella": "uus",
    "uuksilla": "uus",
    "uudelta": "uus",
    "uuksilta": "uus",
    "uudelle": "uus",
    "uuksille": "uus",
    "uutena": "uus",
    "uuksina": "uus",
    "uudeksi": "uus",
    "uuksiksi": "uus",
    "uuksin": "uus",
    "uudetta": "uus",
    "uuksitta": "uus",
    "uuksineen": "uus",
    "uuteni": "uus",
    "uutemme": "uus",
    "uutesi": "uus",
    "uutenne": "uus",
    "uutensa": "uus",
    # -tti: https://en.wiktionary.org/wiki/luotti
    "ttien": "tti",
    "ttia": "tti",
    "ttiä": "tti",
    "tteja": "tti",
    "ttejä": "tti",
    "tissä": "tti",
    "tiltä": "tti",
    "ttina": "tti",
    "ttinä": "tti",
    "tteinä": "tti",
    "tittä": "tti",
    "ttini": "tti",
    "ttimme": "tti",
    "ttisi": "tti",
    "ttinne": "tti",
    "ttinsa": "tti",
    "ttinsä": "tti",
    # too much noise
    # "mista": "minen",
    # "mistä": "minen",
    # "isten": "inen",  # liikenaisten → liikenainen
    # "aisin": "ainen",  # liikenaisin → liikenainen
    # "aista": "ainen",  # liikenaista  → liikenainen
    # "uutta": "uus",
    # "ttiin": "tti",
    # "teille": "tti",
    # "teiksi": "tti",
    # "teista": "tti",
    # "teilla": "tti",
    # "teilta": "tti",
    # "teillä": "tti",
    # "teiltä": "tti",
    # "teitta": "tti",
    # "teittä": "tti",
    # "teissa": "tti",
    # "teissä": "tti",
    # "tille": "tti",
    # "tiksi": "tti",
    # "tissa": "tti",
    # "titta": "tti",
    # "tilta": "tti",
    # "teistä": "tti",
    # "tteineen": "tti",
    # "tteihin": "tti",
    # "tteina": "tti",
}


def apply_fi(token: str) -> Optional[str]:
    "Apply pre-defined rules for Finnish."
    if len(token) < 10 or token[0].isupper():
        return None
    for ending, base in FINNISH_ENDINGS.items():
        if token.endswith(ending):
            return token[: -len(ending)] + base
    ## others: but not yritteineen/yrite
    # if token.endswith("eineen") and token[-7] != token[-8]:
    #    return token[:-6] + "i"
    ## too rare?
    # äyskäisen → äyskäistä
    # if token.endswith("äisen"):
    #    return token[:-4]
    return None


POLISH_ENDINGS = {
    # -ość
    "ościach": "ość",
    "ościami": "ość",
    "ościom": "ość",
    # "ością": "ość",
    # "ości": "ość",
    # -ować
    "owałem": "ować",
    "owałam": "ować",
    "owaliśmy": "ować",
    "owałeś": "ować",
    "owałaś": "ować",
    "owaliście": "ować",
    # "ował": "ować",
    # "owała": "ować",
    # "owało": "ować",
    # "owali": "ować",
    # "owały": "ować",
    "owałbym": "ować",
    "owałabym": "ować",
    "owalibyśmy": "ować",
    "owałbyś": "ować",
    "owałabyś": "ować",
    "owalibyście": "ować",
    "owałby": "ować",
    "owałaby": "ować",
    "owałoby": "ować",
    "owaliby": "ować",
    "owałyby": "ować",
    "owanie": "ować",
    # -ski
    # "skie": "ski",
    # "skiego": "ski",
    # "skiemu": "ski",
    # "skiej": "ski",
    # "skich": "ski",
    # "skim": "ski",
    # "skimi": "ski",
    # "ską": "ski",
    # "scy": "ski",
    # others, -ać/-eć/-ić/-yć
    "alibyście": "ać",
    "alibyśmy": "ać",
    "iłybyście": "ić",
    "ilibyście": "ić",
    "ilibyśmy": "ić",
    "iłybyśmy": "ić",
    "yłybyście": "yć",
    "ylibyście": "yć",
    "ylibyśmy": "yć",
    "yłybyśmy": "yć",
}


def apply_pl(token: str) -> Optional[str]:
    "Apply pre-defined rules for Polish."
    if len(token) < 10 or token[0].isupper():
        return None
    for ending, base in POLISH_ENDINGS.items():
        if token.endswith(ending):
            return token[: -len(ending)] + base
    return None


RUSSIAN_PREFIXES = {
    "гидро",
    "за",
    "контр",
    "много",
    "микро",
    "недо",
    "пере",
    "под",
    "пред",
    "при",
    "про",
    "радио",
    "раз",
    "рас",
    "само",
    "экстра",
    "электро",
}


RUSSIAN_ENDINGS = {
    # -ость
    "ости": "ость",
    "остью": "ость",
    "остей": "ость",
    "остям": "ость",
    "остями": "ость",
    "остях": "ость",
    # -ство
    "ства": "ство",
    "ств": "ство",
    "ству": "ство",
    "ствам": "ство",
    "ством": "ство",
    "ствами": "ство",
    "стве": "ство",
    "ствах": "ство",
}


def apply_ru(token: str) -> Optional[str]:
    "Apply pre-defined rules for Russian."
    if token.endswith("ё"):
        return token.replace("ё", "е")
    if len(token) < 10 or token[0].isupper() or "-" in token:
        return None
    # token = token.replace("а́", "a")
    # token = token.replace("о́", "o")
    # token = token.replace("и́", "и")
    for ending, base in RUSSIAN_ENDINGS.items():
        if token.endswith(ending):
            return token[: -len(ending)] + base
    return None
