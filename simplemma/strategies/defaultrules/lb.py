import re

from .generic import apply_rules

# Luxembourgish adjective declension: comparative (-er/-em) and superlative
# (-st + declension) markers attached to adjective-forming suffixes. Bare
# declension endings (-e/-en/-t alone) are deliberately excluded: they collide
# with verb infinitives/participles and, after long vowels, need a stem
# shortening (absoluutst -> absolut) that a suffix-only rule can't perform.
DEFAULT_RULES = {
    re.compile(r"(?:rtstem|rtsten|rtster|rtste|rtem|rten|rter|rtst|rte)$"): "rt",
    re.compile(
        r"(?:ertstem|ertsten|ertster|ertste|ertem|erten|erter|ertst|erte)$"
    ): "ert",
    re.compile(r"(?:schstem|schsten|schster|schste|schem|scher|schst)$"): "sch",
    re.compile(r"(?:egstem|egsten|egster|egste|egst|egem|eger)$"): "eg",
    re.compile(r"(?:echstem|echster|echem|echer)$"): "ech",
    re.compile(r"(?:ntstem|ntsten|ntster|ntste|ntem|nten|ntst|nte)$"): "nt",
    re.compile(
        r"(?:iivstem|iivsten|iivster|iivste|iivst|iivt|ivem|iven|iver|ive)$"
    ): "iv",
    re.compile(r"(?:eltem|elten|elter|elte)$"): "elt",
    re.compile(r"(?:tegstem|tegsten|tegster|tegste|tegem|teger|tegst|tege)$"): "teg",
    re.compile(r"(?:aalstem|aalsten|aalster|aalste|aalst|alem|aler)$"): "al",
    re.compile(r"(?:legstem|legsten|legster|legste|legem|leger|legst)$"): "leg",
    re.compile(r"(?:tiivt|tivem|tiven|tiver|tive)$"): "tiv",
    re.compile(r"(?:barem|baren|barer|bare|bart)$"): "bar",
    re.compile(r"(?:arem|aren|arer|are)$"): "ar",
    re.compile(r"(?:entem|enten|enter|ente)$"): "ent",
    re.compile(r"(?:segem|segen|seger|sege|segt)$"): "seg",
    re.compile(r"(?:regem|regen|reger|rege)$"): "reg",
}


def apply_lb(token: str) -> str | None:
    "Apply pre-defined rules for Luxembourgish."
    if len(token) < 6 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
