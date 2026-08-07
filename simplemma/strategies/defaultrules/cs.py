import re


# Czech verb conjugation and adjective declension, mined lemma-first
# (99.35% in-dict).
DEFAULT_RULES = {
    re.compile(r"(?:ického|ickou|ickém|ická)$"): r"ický",
    re.compile(
        r"(?:ovány|ováno|ována|ováni|ujíce|ujte|ován|ujou|ujíc|uju|uj)$"
    ): r"ovat",
    re.compile(r"(?:ského|ských|skými|ském|ským|ské)$"): r"ský",
    re.compile(r"(?:ckých|ckými|ckým|čtí)$"): r"cký",
    re.compile(r"(?:lnými|lnému)$"): r"lný",
    re.compile(r"(?:ními|nímu)$"): r"ní",
    re.compile(r"(?:vého|vému|vém)$"): r"vý",
    re.compile(r"(?:kému)$"): r"ký",
    re.compile(r"(?:íma)$"): r"í",
}
