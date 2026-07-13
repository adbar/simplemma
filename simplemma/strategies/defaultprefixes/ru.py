import re

# UD-validated (ru_gsd/ru_syntagrus): "за"/"при" removed -- net harmful,
# fabricating lemmas for lexicalized adverbs (затем->затема). Regex sorts by
# length so order carries no meaning.
RUSSIAN_PREFIXES = [
    "гидро",
    "контр",
    "много",
    "микро",
    "недо",
    "пере",
    "под",
    "пред",
    "про",
    "радио",
    "раз",
    "рас",
    "само",
    "экстра",
    "электро",
]

RU_PREFIX_REGEX = re.compile(
    r"^(" + "|".join(sorted(RUSSIAN_PREFIXES, key=len, reverse=True)) + r")"
)
