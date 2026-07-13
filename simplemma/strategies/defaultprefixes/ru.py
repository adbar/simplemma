import re

# UD-validated (training/data/affix_eval/, ru_gsd tune / ru_syntagrus
# confirm): "за" and "при" fabricated lemmas for lexicalized adverbs/
# particles (затем -> затема x78, примерно -> примерный x57 on confirm)
# despite each also carrying real verbal wins -- net harmful, removed.
# Regex sorts by length so a future addition can never be silently
# shadowed by a shorter existing entry -- list order carries no meaning.
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
