import re

# UD-validated (de_gsd/de_hdt): dropped 27 entries that were unreachable under
# first-match alternation ("herab" shadowed by "her") plus "zu" (fabricated
# zufolge->zufolgen). Regex sorts by length so order carries no meaning.
GERMAN_PREFIXES = [
    "ab",
    "an",
    "auf",
    "aus",
    "be",
    "da",
    "durch",
    "ein",
    "ent",
    "er",
    "gegen",
    "heim",
    "her",
    "hin",
    "hinzu",
    "innen",
    "los",
    "miss",
    "mit",
    "nach",
    "neben",
    "nieder",
    "ran",
    "raus",
    "rein",
    "rum",
    "runter",
    "über",
    "um",
    "unter",
    "ver",
    "vor",
    "weg",
    "weiter",
    "wieder",
    "zer",
]

# (?!zu) blocks prefix+zu-infinitive splits (abzuholen must not be read as
# ab+zuholen) -- unrelated to the "zu" entry removed above.
DE_PREFIX_REGEX = re.compile(
    r"^(" + "|".join(sorted(GERMAN_PREFIXES, key=len, reverse=True)) + r")(?!zu)"
)
