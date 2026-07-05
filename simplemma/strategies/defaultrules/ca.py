import re

from .generic import apply_rules

# Catalan: -ar/-er/-ir verb conjugation (consonant-anchored sub-classes,
# same shape as pt.py/gl.py/es.py), plural/gender endings for nouns and
# adjectives.
#
# Lean build (recipe v4): mined, drop-bad-cells loop, trimmed to the top
# groups covering ~70% of rule firings, merged where signatures repeated.
# 186 groups pre-trim -> 39 final, coverage 57.62%->44.77%, precision
# 99.90%, 0 chains. Catalan merges less than the other Romance languages
# (richer subjunctive/conditional paradigms give fewer byte-identical
# post-stem ending sets across consonant classes).
DEFAULT_RULES = {
    re.compile(
        r"(?:egessen|egesses|egessin|egessis|egéssem|egésseu|egéssim|egéssiu|ejassen|ejasses|ejassin|ejassis|ejàssem|ejàsseu|ejàssim|ejàssiu|ejades|ejaven|ejaves|ejàrem|ejàreu|ejàvem|ejàveu|ejats|ejada|ejant|ejava|ejat|egés|ejam|ejau|ejàs|eja|ege|ejo|ejà)$"
    ): r"ejar",
    re.compile(
        r"(?:tzessen|tzesses|tzessin|tzessis|tzéssem|tzésseu|tzéssim|tzéssiu|tzassen|tzasses|tzassin|tzassis|tzàssem|tzàsseu|tzàssim|tzàssiu|tzaven|tzaves|tzàrem|tzàreu|tzàvem|tzàveu|tzats|tzava|tzat|tzem|tzen|tzeu|tzin|tzis|tzés|tzam|tzau|tzàs|tza|tzà|tzí|tze|tzi|tzo|tz)$"
    ): r"tzar",
    re.compile(
        r"(?:llesses|llessen|llessin|llessis|lléssem|llésseu|lléssim|lléssiu|llasses|llassen|llassin|llassis|llàssem|llàsseu|llàssim|llàssiu|llaven|llaves|llàrem|llàreu|llàvem|llàveu|llant|llava|lleu|llem|llés|llàs|llau)$"
    ): r"llar",
    re.compile(
        r"(?:gesses|gessen|gessin|gessis|géssem|gésseu|géssim|géssiu|jarien|jaries|jaríem|jaríeu|jassen|jasses|jassin|jassis|jàssem|jàsseu|jàssim|jàssiu|javes|jaran|jarem|jaren|jares|jareu|jaria|jaràs|javen|jàrem|jàreu|jàvem|jàveu|jant|java|jarà|jaré|jara|gés|jam|jàs|jau|jo|jà)$"
    ): r"jar",
    re.compile(
        r"(?:nesses|nessen|nessin|nessis|néssem|nésseu|néssim|néssiu|narien|naries|naríem|naríeu|nassen|nassin|nassis|nàssem|nàsseu|nàssim|nàssiu|nares|naves|naren|nareu|naven|nàrem|nàreu|nàvem|nàveu|naran|narem|naria|naràs|nava|narà|naré|nara|nés|nin|nau|nam|nà)$"
    ): r"nar",
    re.compile(
        r"(?:laries|larien|lesses|laríem|laríeu|lessin|lessis|léssim|léssiu|lessen|léssem|lésseu|lassen|lassin|lassis|làssem|làsseu|làssim|làssiu|lares|laria|larem|laren|lareu|laràs|laran|làrem|làreu|làvem|làveu|larà|laré|lara)$"
    ): r"lar",
    re.compile(
        r"(?:zarien|zaries|zaríem|zaríeu|zessen|zesses|zessin|zessis|zéssem|zésseu|zéssim|zéssiu|zassen|zasses|zassin|zassis|zàssem|zàsseu|zàssim|zàssiu|zares|zaran|zarem|zaren|zareu|zaria|zaràs|zaven|zaves|zàrem|zàreu|zàvem|zàveu|zats|zarà|zaré|zava|zara|zat|zem|zen|zin|zés|zeu|zam|zau|zàs|zo|zà|z)$"
    ): r"zar",
    re.compile(
        r"(?:taries|tarien|taríem|taríeu|tassis|tassen|tassin|tàssem|tàsseu|tàssim|tàssiu|tares|taria|taran|tarem|tareu|taràs|taven|tàvem|tàveu|taren|tàrem|tàreu|tarà|taré|tara|tau)$"
    ): r"tar",
    re.compile(
        r"(?:raries|rarien|raríem|raríeu|réssem|résseu|réssim|réssiu|rassen|rassin|ràssem|ràsseu|ràssim|ràssiu|raria|rares|rarem|raren|rareu|raràs|raran|ràrem|ràreu|ràvem|ràveu|rarà|raré|rara)$"
    ): r"rar",
    re.compile(
        r"(?:caries|carien|caríem|caríeu|cassen|cassin|cassis|càssem|càsseu|càssim|càssiu|cares|carem|caren|careu|caràs|caria|caran|càrem|càreu|càvem|càveu|carà|cara|caré|que|cau|cam)$"
    ): r"car",
    re.compile(r"(?:acions)$"): r"ació",
    re.compile(r"(?:tiques)$"): r"tica",
    re.compile(r"(?:àssem|àsseu|àssim|àssiu|aren|àvem|àveu|àrem|àreu)$"): r"ar",
    re.compile(
        r"(?:iries|irien|iríem|iríeu|íssem|ísseu|iràs|irem|ireu|iria|iran|irà|iré)$"
    ): r"ir",
    re.compile(r"(?:iques)$"): r"ica",
    re.compile(r"(?:cions)$"): r"ció",
    re.compile(r"(?:dores)$"): r"dora",
    re.compile(r"(?:lades)$"): r"lada",
    re.compile(r"(?:nades)$"): r"nada",
    re.compile(r"(?:tades)$"): r"tada",
    re.compile(r"(?:rades)$"): r"rada",
    re.compile(r"(?:istes)$"): r"ista",
    re.compile(r"(?:eries)$"): r"eria",
    re.compile(r"(?:ncies)$"): r"ncia",
    re.compile(r"(?:ries)$"): r"ria",
    re.compile(r"(?:ades)$"): r"ada",
    re.compile(r"(?:ques)$"): r"ca",
    re.compile(
        r"(ent|tat|dor|ble|lat|nat|rat|tic|ant|cat|tiu|ari|at|nt|ic|ri|al|it|ni|iu|ll|et|ol|t|c|d|m|g)(?:s)$"
    ): r"\1",
    re.compile(r"(?:ores)$"): r"ora",
    re.compile(r"(?:ines)$"): r"ina",
    re.compile(r"(?:oses)$"): r"osa",
    re.compile(r"(?:lles)$"): r"lla",
    re.compile(r"(?:ites)$"): r"ita",
    re.compile(r"(?:etes)$"): r"eta",
    re.compile(r"(?:ones)$"): r"ona",
    re.compile(r"(?:nies)$"): r"nia",
    re.compile(r"(?:eses)$"): r"esa",
    re.compile(r"(?:gies)$"): r"gia",
    re.compile(r"(?:ies)$"): r"ia",
}

# Closed-class collisions found via the UD consistency scan (train+dev+
# test, always identity-gold across every occurrence): invariant function
# words/adverbs (gràcies "thanks", dimarts "Tuesday", aleshores "then",
# tretze "thirteen", tarannà "manner", magatzem "warehouse", tennis,
# honoris), pluralia tantum (escombraries "garbage", genitals, acaballes
# "final stages"), and common-noun/adjective vs verb-form homographs
# (relleu, neteja, secretaria, agreujant, brillant, actualitzat).
_EXCLUDED = frozenset(
    {
        "gràcies",
        "dimarts",
        "aleshores",
        "relleu",
        "neteja",
        "secretaria",
        "tretze",
        "agreujant",
        "escombraries",
        "tarannà",
        "magatzem",
        "tennis",
        "brillant",
        "genitals",
        "actualitzat",
        "honoris",
        "acaballes",
    }
)


def apply_ca(token: str) -> str | None:
    "Apply pre-defined rules for Catalan."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
