import re
from typing import Optional

from .generic import apply_rules


## Just a demo, the rules are really basic and coverage is not good


DEFAULT_RULES = {
    # adjectives
    # https://en.wiktionary.org/wiki/-line
    re.compile(
        r"(?:lise|list|lisse|lisesse|lises|lisest|lisele|lisel|liselt|liseks|liseni|lisena|liseta|lisega|lised|liste|lisi|listesse|lisisse|listes|lisis|listest|lisist|listele|lisile|listel|lisil|listelt|lisilt|listeks|lisiks|listeni|listena|listeta|listega)$"
    ): "line",
    # https://en.wiktionary.org/wiki/-mine
    re.compile(
        r"(?:mise|mist|misse|misesse|mises|misest|misele|misel|miselt|miseks|miseni|misena|miseta|misega|mised|miste|misi|mistesse|misisse|mistes|misis|mistest|misist|mistele|misile|mistel|misil|mistelt|misilt|misteks|misiks|misteni|mistena|misteta|mistega)$"
    ): "mine",
    # nouns
    # https://en.wiktionary.org/wiki/-dus
    re.compile(
        r"(?:duse|dust|dusse|dusesse|duses|dusest|dusele|dusel|duselt|duseks|duseni|dusena|duseta|dusega|dused|duste|dusi|dustesse|dusisse|dustes|dusis|dustest|dusist|dustele|dusile|dustel|dusil|dustelt|dusilt|dusteks|dusiks|dusteni|dustena|dusteta|dustega)$"
    ): "dus",
    # https://en.wiktionary.org/wiki/-lik
    # https://en.wiktionary.org/wiki/-nik
    re.compile(
        r"(?:iku|ikku|ikusse|ikus|ikust|ikule|ikul|ikult|ikuks|ikuni|ikuna|ikuta|ikuga|ikud|ike|ikudde|ikke|ikusid|ikesse|ikkudesse|ikes|ikkudes|ikest|ikkudest|ikele|ikkudele|ikel|ikkudel|ikelt|ikkudelt|ikeks|ikkudeks|ikeni|ikkudeni|ikena|ikkudena|iketa|ikkudeta|ikega|ikkudega)$"
    ): "ik",
    # https://en.wiktionary.org/wiki/-kond
    re.compile(
        r"(?:konna|konda|konnasse|konnas|konnast|konnale|konnal|konnalt|konnaks|konnani|konnana|konnata|konnaga|konnad|kondade|kondi|kondasid|kondadesse|konnisse|kondades|konnis|kondadest|konnist|kondadele|konnile|kondadel|konnil|kondadelt|konnilt|kondadeks|konniks|kondadeni|kondadena|kondadeta|kondadega)$"
    ): "kond",
}


def apply_et(token: str) -> Optional[str]:
    "Apply pre-defined rules for Estonian."
    if len(token) < 8 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
