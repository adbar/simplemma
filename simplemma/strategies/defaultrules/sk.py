import re

from .generic import apply_rules

# Slovak noun/adjective declension and verb conjugation; cells that failed
# on UD real text despite >=99% in-dict (skej/ckej, áte, tému, rmi) dropped.
DEFAULT_RULES = {
    re.compile(r"(?:nosti|ností)$"): r"nosť",
    re.compile(r"(?:ostiach|ostiam|osťami|osťou)$"): r"osť",
    re.compile(r"(?:ávam|áva)$"): r"ávať",
    re.compile(r"(?:ického|ickému|ickou|ickom|ická)$"): r"ický",
    re.compile(
        r"(?:zujeme|zujete|zujem|zuješ|zujme|zujte|zujúc|zuje|zujú|zuj)$"
    ): r"zovať",
    re.compile(
        r"(?:tujeme|tujete|tujem|tuješ|tujme|tujte|tujúc|tuje|tujú|tuj)$"
    ): r"tovať",
    re.compile(
        r"(?:rujeme|rujete|rujem|ruješ|rujme|rujte|rujúc|ruje|rujú|ruj)$"
    ): r"rovať",
    re.compile(r"(?:koví)$"): r"kový",
    re.compile(r"(?:stvami|stiev|stva|stve|stvu)$"): r"stvo",
    re.compile(r"(?:vate|vame|vaj|vaš)$"): r"vať",
    re.compile(r"(?:ová|ovú)$"): r"ový",
    re.compile(r"(?:káme|kaj|káš)$"): r"kať",
    re.compile(r"(?:ského|skému|ským|skú|skí)$"): r"ský",
    re.compile(r"(?:ckým|cké|ckí|ckú)$"): r"cký",
    re.compile(r"(?:haj)$"): r"hať",
    re.compile(r"(?:eného|enému|eným|ené)$"): r"ený",
    re.compile(r"(?:íkoch|íkom|íkov)$"): r"ík",
    re.compile(r"(?:čným)$"): r"čný",
    re.compile(r"(?:ikoch|ikov)$"): r"ik",
    re.compile(r"(?:ajúc|ajme|ajte|ali|ala|alo|ajú|al)$"): r"ať",
    re.compile(r"(?:vého|vému|vým|vé)$"): r"vý",
    re.compile(r"(?:keho|kemu|kych|kymi|kym|ki)$"): r"ky",
    re.compile(r"(?:nych|nymi|neho|nemu|nym)$"): r"ny",
    re.compile(r"(?:tého|tým|té)$"): r"tý",
    re.compile(r"(?:tvom)$"): r"tvo",
    re.compile(r"(?:inou)$"): r"ina",
    re.compile(r"(?:ila|ili|ilo|il|iš)$"): r"iť",
    re.compile(r"(?:ých|ými)$"): r"ý",
    re.compile(r"(?:iou|ii)$"): r"ia",
    re.compile(r"(?:kmi)$"): r"k",
    re.compile(r"(?:čke)$"): r"čka",
    re.compile(r"(?:nmi)$"): r"n",
}

# invariant words, homographs (správa), and -inou possessives whose lemma is
# not the -ina noun the cell assumes (matkin)
_EXCLUDED = frozenset(
    {
        "anonym",
        "detail",
        "festival",
        "gazdinou",
        "interval",
        "jedinou",
        "kabala",
        "mamkinou",
        "matkinou",
        "medzitým",
        "michal",
        "mnohými",
        "ospalo",
        "predtým",
        "prevzali",
        "príliš",
        "príval",
        "prostredníctvom",
        "samojedinou",
        "správa",
        "švagrinou",
        "testinou",
        "ujčinou",
        "väčšinou",
        "vrstiev",
        "vrstva",
        "vytrvalo",
        "zdvorilo",
        "zúfalo",
    }
)


def apply_sk(token: str) -> str | None:
    "Apply pre-defined rules for Slovak."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
