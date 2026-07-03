import re

from .generic import apply_rules

# Czech: verb conjugation (-ovat/-vat/-nout/-out families), adjective
# declension (-ký/-ný/-ní and their productive compounds -ský/-cký/-ický/
# -elný/-ový/...), and a handful of noun suffixes. A few narrow alternatives
# are deliberately left out even though their siblings are kept: -ké (heavily
# polluted by the productive ne- negation prefix: nedaleké -> daleky, not
# nedaleky), -ních (collides with -eň nouns whose oblique stem changes:
# ohnich is genitive plural of oheň, not an adjective), -ímu (collides with
# the productive -ejší/-ější comparative infix), -vými (collides with -ův
# possessive adjectives: orlovými is instrumental plural of orluv, not
# orlový).
# Trimmed to the top rule groups covering ~90% of rule firings.
DEFAULT_RULES = {
    re.compile(
        r"(?:ovavše|ovavši|ujíce|ována|ováni|ováno|ovány|ovav|ujou|ujte|ujíc|ován|uju|uj)$"
    ): "ovat",
    re.compile(r"(?:ického|ickému|ickou|ickém|ická|ičtí)$"): "ický",
    re.compile(r"(?:nících|níkovi|níkem|níkům|níci|níka|níku|níky|níků)$"): "ník",
    re.compile(r"(?:elného|elnému|elném)$"): "elný",
    re.compile(r"(?:ostech|ostem|ostmi)$"): "ost",
    re.compile(r"(?:árnách|árnám|árno|árnu|árny|árně|árn)$"): "árna",
    re.compile(r"(?:vavše|vavši|vána|váni|váno|vány|vav|ván)$"): "vat",
    re.compile(r"(?:ckého|ckému|ckých|ckými|ckém|ckým|cká|čtí)$"): "cký",
    re.compile(r"(?:ského|skému|ských|skými|ském|ským|ské)$"): "ský",
    re.compile(r"(?:íkovi|íkem|íkům|íku|íky|íků|íka)$"): "ík",
    re.compile(r"(?:nuvše|nuvši|nuta|nuti|nuto|nuty|nula|nut|nuv)$"): "nout",
    re.compile(r"(?:ového|ovému|ovém)$"): "ový",
    re.compile(r"(?:ivého|ivému|ivých|ivými|ivém|ivým|ivá|ivé)$"): "ivý",
    re.compile(r"(?:lních|lního|lníma|lními|lnímu|lním)$"): "lní",
    re.compile(r"(?:lnému|lnými)$"): "lný",
    re.compile(r"(?:eného|enému|enými|eném)$"): "ený",
    re.compile(r"(?:tních|tního|tníma|tními|tnímu|tním)$"): "tní",
    re.compile(r"(?:čních|čního|čníma|čními|čnímu|čním)$"): "ční",
    re.compile(r"(?:anému|anými|aném|aným)$"): "aný",
    re.compile(r"(?:nicím|nici|nicí|nic)$"): "nice",
    re.compile(r"(?:ního|níma|ními|nímu|ním)$"): "ní",
    re.compile(r"(?:řovi|řem|řům|řů)$"): "ř",
    re.compile(r"(?:ákem|ákům|áku|áky)$"): "ák",
    re.compile(r"(?:lých|lými|lým)$"): "lý",
    re.compile(r"(?:címa|cími|címu)$"): "cí",
    re.compile(r"(?:íma|ími)$"): "í",
    re.compile(r"(?:sem|su|sů)$"): "s",
}


def apply_cs(token: str) -> str | None:
    "Apply pre-defined rules for Czech."
    if len(token) < 6 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
