import re

from .generic import apply_rules

# Romanian verb conjugation and noun/adjective endings (fused definite
# articles included), mined lemma-first (99.73% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:tase|tai|tam|tăm|tau|tez)$"): r"ta",
    re.compile(r"(?:zează|zară|zase|zași|zezi|zeze|zau|zai|zam|zăm|zez)$"): r"za",
    re.compile(r"(?:nase|nau|nam|nai|năm)$"): r"na",
    re.compile(r"(?:ităților|itățile|ității|ități)$"): r"itate",
    re.compile(r"(?:aserăți|aserăm|aseră|aseși|arăți|arăm|asem|aţi|atu)$"): r"a",
    re.compile(r"(?:torule)$"): r"tor",
    re.compile(r"(?:bilului|bililor|bilul|bilii|bili)$"): r"bil",
    re.compile(r"(?:ațiilor|ațiile|ația)$"): r"ație",
    re.compile(r"(?:aților|atule)$"): r"at",
    re.compile(r"(?:iților|itule)$"): r"it",
    re.compile(r"(?:orului|orul)$"): r"or",
    re.compile(r"(?:icului|icul)$"): r"ic",
    re.compile(r"(?:alului|alul|ali)$"): r"al",
    re.compile(r"(?:osul)$"): r"os",
    re.compile(r"(?:arului|arul)$"): r"ar",
    re.compile(r"(?:erului|erul)$"): r"er",
    re.compile(r"(?:ivului|ivul)$"): r"iv",
    re.compile(r"(?:tului|tul)$"): r"t",
    re.compile(r"(?:irăți|irăm|isem|iţi|itu)$"): r"i",
    re.compile(r"(?:nului|nul)$"): r"n",
    re.compile(r"(?:irile|irea|ireo)$"): r"ire",
    re.compile(r"(?:ările)$"): r"are",
    re.compile(r"(?:mului|mul)$"): r"m",
    re.compile(r"(?:sului)$"): r"s",
    re.compile(r"(?:izați)$"): r"izat",
    re.compile(r"(?:tați|tată)$"): r"tat",
    re.compile(r"(?:uite|uită|uiți)$"): r"uit",
    re.compile(r"(?:cată|cați)$"): r"cat",
    re.compile(r"(?:niți|nită)$"): r"nit",
    re.compile(r"(?:zată)$"): r"zat",
    re.compile(r"(?:nați)$"): r"nat",
    re.compile(r"(?:ției)$"): r"ție",
    re.compile(r"(?:atea)$"): r"ate",
    re.compile(r"(?:iată)$"): r"iat",
    re.compile(r"(?:lați)$"): r"lat",
}

# genuine collisions only (identity lemmas, participle-vs-noun homographs,
# vowel-changing plurals, irregulars); UD preferring the infinitive over the
# dict's participle lemma is a convention difference, not stoplisted
_EXCLUDED = frozenset(
    {
        "înspăimânțaseși",
        "admirăm",
        "rămaseră",
        "vreunul",
        "țările",
        "păsările",
        "flăcările",
        "destul",
        "stimul",
        "vehicul",
        "neconformitatea",
        "conduită",
        "judecată",
        "bucată",
        "turburatu",
        "endonimul",
        "stabili",
    }
)


def apply_ro(token: str) -> str | None:
    "Apply pre-defined rules for Romanian."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
