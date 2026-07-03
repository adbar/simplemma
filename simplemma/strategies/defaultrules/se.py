import re

from .generic import apply_rules

# Northern Sámi verb conjugation (past/conditional/potential moods of the
# -it/-at/-ut/-t verb classes). Consonant gradation makes many forms
# irregular; these cells are the paradigm-anchored suffixes that reduce
# cleanly back to the infinitive.
DEFAULT_RULES = {
    re.compile(
        r"(?:ivččiide|ivččiiga|ivččiime|ibeahtti|eažžaba|ibēhtet|eiddet|eimmet"
        r"|eahppi|eatnot|eaččan|eaččat|eažžat|ivččen|ivččet|ivččii|eadnu|ēhket"
        r"|edjen|edjet|eidde|eigga|eimme|ēhpet|eačča|eažžá|ežžet|ivčče|edje"
        r"|etne|eaba|ežže|imin|eaš|iba)$"
    ): "it",
    re.compile(
        r"(?:beahtti|jeadnot|jeahkki|jeahkku|vččiiga|vččiime|bēhtet|jeadnu"
        r"|jēhket|jēhkon|jēhkos|jēhkot|jētnot|jetne|vččen|vččet|vččii|včče)$"
    ): "t",
    re.compile(r"(?:abeahtti|abēhtet|amin)$"): "at",
    re.compile(r"(?:tadet|tamet|taset|taska|tade)$"): "ta",
    re.compile(r"(?:ubeahtti|ubēhtet|uba|ume)$"): "ut",
    re.compile(r"(?:iska)$"): "i",
    re.compile(r"(?:uset|uska)$"): "u",
}


def apply_se(token: str) -> str | None:
    "Apply pre-defined rules for Northern Sámi."
    if len(token) < 6 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
