import re

# UD-validated (uk_iu): clean accept, no harmful entry. Regex sorts by length
# so order carries no meaning. See README.md "Slavic prefix wave".
UKRAINIAN_PREFIXES = [
    "по",
    "за",
    "ви",
    "на",
    "при",
    "про",
    "роз",
    "пере",
    "від",
    "до",
    "під",
    "об",
    "без",
]

UK_PREFIX_REGEX = re.compile(
    r"^(" + "|".join(sorted(UKRAINIAN_PREFIXES, key=len, reverse=True)) + r")"
)
