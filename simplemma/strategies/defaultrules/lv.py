import re
from typing import Optional

from .generic import apply_rules

# https://en.wiktionary.org/wiki/Category:Latvian_suffixes

DEFAULT_RULES = {
    # feminine nouns
    re.compile(r"(?:āju|ājas|ājai|ājam|ājās)$"): "āja",
    re.compile(r"(?:ēju|ējas|ējai|ējam|ējās)$"): "ēja",
    re.compile(r"(?:ieci|ieces|iecei|iecē|ieču|iecēm|iecēs)$"): "iece",
    re.compile(r"(?:ieti|ietes|ietei|ietē|ietes|iešu|ietēm|ietēs)$"): "iete",
    re.compile(r"(?:iju|ijas|ijai|ijam)$"): "ija",
    re.compile(r"(?:ību|ības|ībai|ībām|ībās)$"): "ība",
    re.compile(r"(?:īgu|īga|īgam|īgi|īgus|īgiem|īgos|īgas|īgai|īgā|īgām|īgās)$"): "īgs",
    re.compile(r"(?:īva|īvu|īvam|īvas|īvai|īvus|īviem|īvos|īvā|īvām|īvās)$"): "īvs",
    re.compile(r"(?:šanu|šanas|šanai|šanā|šanām|šanās)$"): "šana",
    re.compile(r"(?:umu|uma|umam|umā|umām|umās)$"): "ums",  # |um
    # masculine nouns
    re.compile(r"(?:āju|āja|ājam|āj|āji|ājus|ājiem|ājos)$"): "ājs",
    re.compile(r"(?:iņu|iņa|iņam|iņ|iņi|iņus|iņiem|iņos)$"): "iņš",
    re.compile(
        r"(?:isku|iska|iskam|iskā|iski|iskus|iskiem|isko|iskos|iskai|iskas|iskām|iskās)$"
    ): "isks",
    re.compile(r"(?:ismu|isma|ismam|ismā|iski|ism)$"): "isms",
    re.compile(r"(?:īti|īša|ītim|ītī|īt|īši|īšus|īšu|īšiem|īšos)$"): "ītis",
    re.compile(r"(?:kli|kļa|klim|klī|kļi|kļus|kļiem|kļos)$"): "klis",
    re.compile(r"(?:nieku|nieka|niekam|niekā|nieki|niekus|niekiem|niekos)$"): "nieks",
    re.compile(r"(?:ni|ņa|nim|nī|ņi|ņus|ņu|ņiem|ņos)$"): "nis",
    # fallback
    re.compile(r"(?:as|ai|ā|ām|ās)$"): "a",
    re.compile(r"(?:ei|es|ē|ēm|ēs)$"): "e",
    re.compile(r"(?:is|im|ī|iem|īs)$"): "is",
    # re.compile(r"(?:os|us)$"): "s",
    # re.compile(r"(?:ēto|ēts)$"): "ēt",
}


def apply_lv(token: str) -> Optional[str]:
    "Apply pre-defined rules for Latvian."
    if len(token) < 5:
        return None

    return apply_rules(token, DEFAULT_RULES)
