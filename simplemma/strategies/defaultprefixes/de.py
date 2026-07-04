import re

# UD-validated (training/data/affix_eval/, de_gsd tune / de_hdt confirm):
# 27 entries that were proper prefixes of another entry above them were
# statically unreachable under first-match alternation (e.g. "herab" could
# never fire because "her" always won first) and "zu" fabricated lemmas for
# lexicalized function words (zufolge -> zufolgen, 109 tokens on de_hdt).
# Both removals verified 0-diff / net-positive. Regex below sorts by length
# so a future addition can never be silently shadowed by a shorter existing
# entry -- list order carries no meaning.
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
