import re

from .generic import apply_rules

# Catalan: -ar/-ir verb conjugation (per-consonant sub-classes) and
# noun/adjective plural endings. Lemma-first build (mine -> trim(0.70) ->
# refine -> subsume): 23 groups, 39.46% coverage, 99.81% in-dict.
DEFAULT_RULES = {
    re.compile(
        r"(?:egessen|egesses|egessin|egessis|egéssem|egésseu|egéssim|egéssiu"
        r"|ejassen|ejasses|ejassin|ejassis|ejaves|ejada|ejant|egem|egen|egeu"
        r"|egin|ejat|egés|ejam|ejau|ejàs|eja|ege|ejo|ejà)$"
    ): r"ejar",
    re.compile(r"(?:llaves|llant|lleu|llem|llés)$"): r"llar",
    re.compile(
        r"(?:nesses|nessen|nessin|nessis|néssem|nésseu|néssim|néssiu|naries"
        r"|nassen|nassin|nassis|nares|naves|nareu|narem|naràs|narà|nara|nés"
        r"|nàs|nin|nau|nam|nà)$"
    ): r"nar",
    re.compile(
        r"(?:laries|lesses|lessin|lessis|léssim|léssiu|lessen|léssem|lésseu"
        r"|lassen|lassin|lassis|lares|larem|lareu|laràs|larà|lara|làs)$"
    ): r"lar",
    re.compile(
        r"(?:taries|tasses|tassis|tassen|tassin|tares|taves|tarem|tareu"
        r"|taràs|tarà|tara|tàs|tau)$"
    ): r"tar",
    re.compile(
        r"(?:raries|réssem|résseu|réssim|réssiu|rares|rarem|rareu|raràs"
        r"|rarà|rara)$"
    ): r"rar",
    re.compile(
        r"(?:zaries|zessen|zesses|zessin|zessis|zéssem|zésseu|zéssim|zéssiu"
        r"|zares|zarem|zareu|zaràs|zaves|zarà|zat|zem|zen|zin|zés|zeu|zo|zà)$"
    ): r"zar",
    re.compile(r"(?:jaries|jarem|jares|jareu|jaràs|jarà|jara)$"): r"jar",
    re.compile(r"(?:caries|que|cau|cam)$"): r"car",
    re.compile(
        r"(?:arien|aríem|aríeu|àssem|àsseu|àssim|àssiu|aria|aren|aven|aran"
        r"|àvem|àveu|àrem|àreu|ava|aré|ars)$"
    ): r"ar",
    re.compile(r"(?:iries|irien|iríem|iríeu|íssem|ísseu|iria|iran|iré)$"): r"ir",
    re.compile(r"(?:cions)$"): r"ció",
    re.compile(r"(?:ents)$"): r"ent",
    re.compile(r"(?:dors)$"): r"dor",
    re.compile(r"(?:ants)$"): r"ant",
    re.compile(r"(?:tius)$"): r"tiu",
    re.compile(r"(?:als)$"): r"al",
    re.compile(r"(?:lls)$"): r"ll",
    re.compile(r"(?:tza)$"): r"tzar",
    re.compile(r"(?:cs)$"): r"c",
    re.compile(r"(?:ds)$"): r"d",
    re.compile(r"(?:ms)$"): r"m",
    re.compile(r"(?:gs)$"): r"g",
}

# The bare "z"->"zar" alt was dropped: its real-text firings were all
# Spanish surnames (Fernández), not verbs. Below, finite collisions from
# the consistency scan + worktree diff: invariant words/pluralia tantum,
# irregular-verb forms (anar, fer), verb forms whose stem extends a longer
# alternative, and proper nouns.
_EXCLUDED = frozenset(
    {
        "relleu",
        "neteja",
        "secretaria",
        "comissaria",
        "escombraries",
        "tarannà",
        "magatzem",
        "brillant",
        "genitals",
        "actualitzat",
        "gimnàs",
        "expolítics",
        "impediments",
        "dessacralitzat",
        "globalitzat",
        "avaria",
        "passejada",
        "aniran",
        "anirien",
        "farien",
        "declara",
        "declaren",
        "separen",
        "preparen",
        "confraries",
        "varien",
        "millàs",
        "llaràs",
        "ciments",
        "comediants",
        "manzanares",
    }
)


def apply_ca(token: str) -> str | None:
    "Apply pre-defined rules for Catalan."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
