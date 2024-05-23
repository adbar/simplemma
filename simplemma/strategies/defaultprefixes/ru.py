import re

RUSSIAN_PREFIXES = [
    "гидро",
    "за",
    "контр",
    "много",
    "микро",
    "недо",
    "пере",
    "под",
    "пред",
    "при",
    "про",
    "радио",
    "раз",
    "рас",
    "само",
    "экстра",
    "электро",
]

RU_PREFIX_REGEX = re.compile(r"^(" + "|".join(RUSSIAN_PREFIXES) + ")")
