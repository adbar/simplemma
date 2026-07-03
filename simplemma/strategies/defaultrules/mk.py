import re

from .generic import apply_rules

# Macedonian definite-article and plural declension. Case/number markers
# (-ва/-на/-та definite singular, -ве/-не/-те definite plural, -и plural)
# attach after the noun's own final consonant cluster. Order matters: the
# broad -а family is checked first (it's usually correct even for stems with
# an extra consonant cluster), and the more specific families narrow down
# the exceptions -- reversing this order leaves -а with only the irregular
# leftovers and its precision drops below the bar.
# Trimmed to the top rule groups covering ~90% of rule firings.
DEFAULT_RULES = {
    re.compile(r"(?:ана|ата)$"): "а",
    re.compile(r"(?:кава|кана|ката|киве|кине|ките|кање|ке)$"): "ка",
    re.compile(r"(?:ијава|ијана|ијата|ииве|иине|иите|ијо|ии)$"): "ија",
    re.compile(r"(?:цава|цана|цата|циве|цине|ците)$"): "ца",
    re.compile(r"(?:чињава|чињана|чињата|чево|чето)$"): "че",
    re.compile(r"(?:нана|ната|ниве|ните)$"): "на",
    re.compile(r"(?:твава|твана|твата|тва)$"): "тво",
    re.compile(r"(?:рање|рата|риве|рине|рите)$"): "ра",
    re.compile(r"(?:уван)$"): "ува",
    re.compile(r"(?:зава|зана|зата|зиве|зине|зите)$"): "за",
    re.compile(r"(?:змов|змон|змот|зму)$"): "зам",
}


def apply_mk(token: str) -> str | None:
    "Apply pre-defined rules for Macedonian."
    if len(token) < 6 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
