import re

# 2-letter prefixes are theoretically already accounted for by the current AFFIXLEN parameter
GERMAN_PREFIXES = [
    "ab",
    "an",
    "auf",
    "aus",
    "be",
    "bei",
    "da",
    "dar",
    "darin",
    "davor",
    "durch",
    "ein",
    "ent",
    "entgegen",
    "er",
    "gegen",
    "heim",
    "her",
    "herab",
    "heran",
    "herauf",
    "heraus",
    "herbei",
    "herein",
    "herum",
    "herunter",
    "hervor",
    "hin",
    "hinab",
    "hinauf",
    "hinaus",
    "hinein",
    "hinten",
    "hinter",
    "hinunter",
    "hinweg",
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
    "voran",
    "voraus",
    "vorbei",
    "vorher",
    "vorüber",
    "weg",
    "weiter",
    "wieder",
    "zer",
    "zu",
]

DE_PREFIX_REGEX = re.compile(r"^(" + "|".join(GERMAN_PREFIXES) + ")(?!zu)")
