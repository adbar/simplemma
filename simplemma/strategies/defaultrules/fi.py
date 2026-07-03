import re

from .generic import apply_rules

# Cells pruned to >=99% in-dict (tolerating pluralia + hyphen-compound
# artifacts). Dropped: the -tti case cells (kenttä/rotta homographs, kept only
# possessive/partitive) and the -isi* plural-oblique -inen cells (isä/lisä and
# poliisi collisions); the singular -ise* cells are kept.

DEFAULT_RULES = {
    # -minen verbal nouns https://en.wiktionary.org/wiki/-minen
    re.compile(r"(?:miset|misen|misten|miseen|misia|misiä|misiin|misin)$"): "minen",
    # -inen nouns/adjectives (singular oblique + possessive cells)
    re.compile(
        r"(?:isettä|isetta|isestä|isesta|isessä|isessa|isensä|isensa|isenne|iseltä|iselta|isellä|iselle|isella|iseksi|isesi|iseni|iseen)$"
    ): "inen",
    # -ainen https://en.wiktionary.org/wiki/-ainen
    re.compile(r"(?:aisen|aiset|aisia)$"): "ainen",
    # -uus abstract nouns https://en.wiktionary.org/wiki/nerokkuus
    re.compile(
        r"(?:uudet|uuden|uuksien|uuksiin|uuksia|uudessa|uuksissa|uuteen|uudella|uuksilla|uudelta|uuksilta|uudelle|uuksille|uutena|uuksina|uudeksi|uuksiksi|uuksin|uudetta|uuksitta|uuksineen|uuteni|uutemme|uutesi|uutenne|uutensa)$"
    ): "uus",
    # -us nouns (uks- stem)
    re.compile(
        r"(?:uksista|uksilta|uksille|uksilla|uksiksi|uksesta|uksessa|ukselta|ukselle|uksella|ukseksi|uksina|uksien|uksena|ukseen|uksia|ukset|uksen)$"
    ): "us",
    # -ys nouns (yks- stem)
    re.compile(
        r"(?:yksistä|yksiltä|yksillä|yksille|yksiksi|yksestä|yksessä|ykseltä|yksellä|ykselle|ykseksi|yksinä|yksien|yksenä|ykseen|yksiä|ykset|yksen)$"
    ): "ys",
    # -tti nouns (possessive + plural partitive) https://en.wiktionary.org/wiki/luotti
    re.compile(r"(?:ttinsä|ttinsa|ttinne|ttimme|ttisi|ttini|ttejä|tteja)$"): "tti",
}


def apply_fi(token: str) -> str | None:
    "Apply pre-defined rules for Finnish."
    if len(token) < 10 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
