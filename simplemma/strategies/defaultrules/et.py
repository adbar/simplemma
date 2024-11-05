import re
from typing import Optional

from .generic import apply_rules

DEFAULT_RULES = {
    # adjectives
    # https://en.wiktionary.org/wiki/-line
    re.compile(
        r"(?:lise|list|lisse|lisesse|lises|lisest|lisele|lisel|liselt|liseks|liseni|lisena|liseta|lisega|lised|liste|lisi|listesse|lisisse|listes|lisis|listest|lisist|listele|lisile|listel|lisil|listelt|lisilt|listeks|lisiks|listeni|listena|listeta|listega)$"
    ): "line",
    # nouns
    # https://en.wiktionary.org/wiki/-kond
    re.compile(
        r"(?:konna|konda|konnasse|konnas|konnast|konnale|konnal|konnalt|konnaks|konnani|konnana|konnata|konnaga|konnad|kondade|kondi|kondasid|kondadesse|konnisse|kondades|konnis|kondadest|konnist|kondadele|konnile|kondadel|konnil|kondadelt|konnilt|kondadeks|konniks|kondadeni|kondadena|kondadeta|kondadega)$"
    ): "kond",
    # https://en.wiktionary.org/wiki/-nik
    re.compile(
        r"(?:niku|nikku|nikusse|nikus|nikust|nikule|nikul|nikult|nikuks|nikuni|nikuna|nikuta|nikuga|nikud|nike|nikudde|nikke|nikusid|nikesse|nikkudesse|nikes|nikkudes|nikest|nikkudest|nikele|nikkudele|nikel|nikkudel|nikelt|nikkudelt|nikeks|nikkudeks|nikeni|nikkudeni|nikena|nikkudena|niketa|nikkudeta|nikega|nikkudega)$"
    ): "nik",
}


def apply_et(token: str) -> Optional[str]:
    "Apply pre-defined rules for Estonian."
    if len(token) < 10 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
