from .generic import SuffixRules

# Czech verb conjugation and adjective declension, mined lemma-first
# (99.35% in-dict).
DEFAULT_RULES = SuffixRules(
    {
        "ický": "ického ickou ickém ická",
        "ovat": "ovány ováno ována ováni ujíce ujte ován ujou ujíc uju uj",
        "ský": "ského ských skými ském ským ské",
        "cký": "ckých ckými ckým čtí",
        "lný": "lnými lnému",
        "ní": "ními nímu",
        "vý": "vého vému vém",
        "ký": "kému",
        "í": "íma",
    },
    min_len=6,
    caps=True,
)


apply_cs = DEFAULT_RULES.apply
