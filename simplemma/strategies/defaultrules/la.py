import re

from .generic import apply_rules

# Latin verb conjugation and noun/adjective declension, mined lemma-first
# (99.69% in-dict). The (?<=..) stem floor keeps whole-word or 1-char-stem
# matches from stripping to a bare target (abimus -> *o, antium -> *ans).
DEFAULT_RULES = {
    re.compile(r"(?<=..)(?:tionis|tione)$"): r"tio",
    re.compile(r"(?<=..)(?:ientis|ientem|ientes|ienti|iente)$"): r"iens",
    re.compile(
        r"(?<=..)(?:averunt|avisset|averant|averint|avissem|avisses|avistis"
        r"|assemus|assetis|abitis|abatis|abamus|abimus|avisse|averit"
        r"|averam|averat|averas|averim|avimus|avisti|aritis|assent|arimus"
        r"|abant|abunt|atote|avero|astis|asses|assem|asset|arunt|arint"
        r"|anto|abis|abam|abas|abit|abat|avit|asse|asti|arim|arit|abo|ō)$"
    ): r"o",
    re.compile(r"(?<=..)(?:turorum|turos|tūrus|tūrum|turi|ture|turo)$"): r"turus",
    re.compile(r"(?<=..)(?:andarum|andis|andas|andam|andae|anda|ande)$"): r"andus",
    re.compile(r"(?<=..)(?:antibus|antium|antis|antem|antes|anti|ante|āns)$"): r"ans",
    re.compile(r"(?<=..)(?:endarum|endae|enda)$"): r"endus",
    re.compile(r"(?<=..)(?:ionibus|ionem|iones|ionum|iōnis|ioni)$"): r"io",
    re.compile(r"(?<=..)(?:entibus|entium|ēns)$"): r"ens",
    re.compile(r"(?<=..)(?:tata)$"): r"tatus",
    re.compile(r"(?<=..)(?:ioribus|ioris|iorem|iores|iora|iore|iori)$"): r"ior",
    re.compile(r"(?<=..)(?:surorum|suros|sūrum|sūrus|sure|suri|suro)$"): r"surus",
    re.compile(r"(?<=..)(?:toribus|torem|tores|tore)$"): r"tor",
    re.compile(r"(?<=..)(?:atarum|atas|atos|atae|atam|ātus|āta)$"): r"atus",
    re.compile(r"(?<=..)(?:ndorum|ndos)$"): r"ndus",
    re.compile(r"(?<=..)(?:ebitis|ebimus|eamus|ebunt|etote|eant|ebit|eat|ebo)$"): r"eo",
    re.compile(r"(?<=..)(?:centis|centi)$"): r"cens",
    re.compile(r"(?<=..)(?:dentis)$"): r"dens",
    re.compile(r"(?<=..)(?:simae|simam|simas|simis|simos|sima|simo|simi)$"): r"simus",
    re.compile(r"(?<=..)(?:tatem|tates|tātis|tās)$"): r"tas",
    re.compile(r"(?<=..)(?:camus|cant|cat)$"): r"co",
    re.compile(r"(?<=..)(?:tamus|tant|tat)$"): r"to",
    re.compile(r"(?<=..)(?:nsium|nsia)$"): r"nsis",
    re.compile(r"(?<=..)(?:ēnsis)$"): r"ensis",
    re.compile(r"(?<=..)(?:urum)$"): r"urus",
    re.compile(r"(?<=..)(?:ōris)$"): r"or",
    re.compile(r"(?<=..)(?:icos)$"): r"icus",
    re.compile(r"(?<=..)(?:bile)$"): r"bilis",
    re.compile(r"(?<=..)(?:rios)$"): r"rius",
    re.compile(r"(?<=..)(?:ctos)$"): r"ctus",
    re.compile(r"(?<=..)(?:itos)$"): r"itus",
    re.compile(r"(?<=..)(?:rati)$"): r"ratus",
}

# idempotence chains (centēsimō -> centēsimo -> *centēsimus) plus one invariant
_EXCLUDED = frozenset(
    {
        "centēsimō",
        "cinnabarim",
        "dēcantō",
        "mūsimō",
        "trānsplantō",
        "tūtissimō",
        "fortasse",
    }
)


def apply_la(token: str) -> str | None:
    "Apply pre-defined rules for Latin."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
