import re

from .generic import apply_rules

# Czech: verb conjugation (-ovat/-it families) and adjective declension
# (-ský/-cký/-ický/-ný families). Lemma-first build (mine -> trim(0.70) ->
# refine -> subsume): 10 groups, 9.95% coverage, 99.35% in-dict.
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
    re.compile(r"(?:ivši|ivše)$"): r"it",
    re.compile(r"(?:kému)$"): r"ký",
    re.compile(r"(?:íma)$"): r"í",
}


def apply_cs(token: str) -> str | None:
    "Apply pre-defined rules for Czech."
    # hyphenated compounds only get their tail lemmatized
    # (vězni-straníci), an error class rules can never fix -- skip
    return apply_rules(token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True)
