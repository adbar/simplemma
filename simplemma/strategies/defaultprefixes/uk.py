import re

# UD-validated (training/data/affix_eval/, uk_iu tune(dev)/confirm(test),
# 2026-07-04 prefix-expansion wave -- see training/data/affix_eval/README.md
# "Prefix-strategy audit" for the de/ru precedent and
# "Slavic prefix wave" for this language's numbers): clean accept, no
# harmful entry found (rule-(d) audit: worsened set stays under 5 tokens
# on confirm, no coherent counter-class). Regex sorts by length so a
# future addition can never be silently shadowed by a shorter entry.
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
