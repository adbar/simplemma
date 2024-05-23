import re
from typing import Optional

from .generic import apply_rules

DEFAULT_RULES = {
    # -minen nouns, ä/ö/y + a/o/u
    # https://en.wiktionary.org/wiki/-minen
    # too much noise: "mista", "mistä"
    re.compile(r"(miset|misen|misten|miseen|misia|misiä|misiin|misin)$"): "minen",
    # -inen nouns
    # too much noise: "isten"
    re.compile(
        r"(?:isissa|isissä|isista|isistä|iseksi|iseen|isella|isellä|iselle|iselta|iseltä|iseni|isensa|isensä|isesi|isessa|isessä|isesta|isestä|isien|isiksi|isilla|isillä|isilta|isiltä|isina|isinä|isineen|isitta|isittä|isemme|isenne|isille|isetta|isettä)$"
    ): "inen",
    # -ainen for more precision
    # liikenaisen → liikenainen
    # liikenaiset → liikenainen
    # liikenaisia → liikenainen
    # too much noise: "aisin", "aista"
    re.compile(r"(?:aisen|aiset|aisia)$"): "ainen",
    # -uus nouns: https://en.wiktionary.org/wiki/nerokkuus
    # too much noise: "uutta"
    re.compile(
        r"(?:uudet|uuden|uuksien|uuksiin|uuksia|uudessa|uuksissa|uuteen|uudella|uuksilla|uudelta|uuksilta|uudelle|uuksille|uutena|uuksina|uudeksi|uuksiksi|uuksin|uudetta|uuksitta|uuksineen|uuteni|uutemme|uutesi|uutenne|uutensa)$"
    ): "uus",
    # -tti: https://en.wiktionary.org/wiki/luotti
    # too much noise: "ttiin", "teille", "teiksi", "teista", "teilla", "teilta", "teillä", "teiltä", "teitta", "teittä", "teissa", "teissä", "tille", "tiksi", "tissa", "titta", "tilta", "teistä", "tteineen", "tteihin", "tteina"
    re.compile(
        r"(?:ttien|ttia|ttiä|tteja|ttejä|tissä|tiltä|ttina|ttinä|tteinä|tittä|ttini|ttimme|ttisi|ttinne|ttinsa|ttinsä)$"
    ): "tti",
}


def apply_fi(token: str) -> Optional[str]:
    "Apply pre-defined rules for Finnish."
    if len(token) < 10 or token[0].isupper():
        return None

    ## others: but not yritteineen/yrite
    # if token.endswith("eineen") and token[-7] != token[-8]:
    #    return token[:-6] + "i"
    ## too rare?
    # äyskäisen → äyskäistä
    # if token.endswith("äisen"):
    #    return token[:-4]

    return apply_rules(token, DEFAULT_RULES)
