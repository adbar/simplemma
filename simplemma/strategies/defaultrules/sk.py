from .generic import SuffixRules

# invariant words, homographs (správa), and -inou possessives whose lemma is
# not the -ina noun the cell assumes (matkin)
_EXCLUDED = frozenset(
    (
        "anonym detail festival gazdinou interval jedinou kabala mamkinou matkinou "
        "medzitým michal mnohými ospalo predtým prevzali príliš príval "
        "prostredníctvom samojedinou správa švagrinou testinou ujčinou väčšinou "
        "vrstiev vrstva vytrvalo zdvorilo zúfalo".split()
    )
)

# Slovak noun/adjective declension and verb conjugation; cells that failed
# on UD real text despite >=99% in-dict (skej/ckej, áte, tému, rmi) dropped.
DEFAULT_RULES = SuffixRules(
    {
        "nosť": "nosti ností",
        "osť": "ostiach ostiam osťami osťou",
        "ávať": "ávam áva",
        "ický": "ického ickému ickou ickom ická",
        "zovať": "zujeme zujete zujem zuješ zujme zujte zujúc zuje zujú zuj",
        "tovať": "tujeme tujete tujem tuješ tujme tujte tujúc tuje tujú tuj",
        "rovať": "rujeme rujete rujem ruješ rujme rujte rujúc ruje rujú ruj",
        "kový": "koví",
        "stvo": "stvami stiev stva stve stvu",
        "vať": "vate vame vaj vaš",
        "ový": "ová ovú",
        "kať": "káme kaj káš",
        "ský": "ského skému ským skú skí",
        "cký": "ckým cké ckí ckú",
        "hať": "haj",
        "ený": "eného enému eným ené",
        "ík": "íkoch íkom íkov",
        "čný": "čným",
        "ik": "ikoch ikov",
        "ať": "ajúc ajme ajte ali ala alo ajú al",
        "vý": "vého vému vým vé",
        "ky": "keho kemu kych kymi kym ki",
        "ny": "nych nymi neho nemu nym",
        "tý": "tého tým té",
        "tvo": "tvom",
        "ina": "inou",
        "iť": "ila ili ilo il iš",
        "ý": "ých ými",
        "ia": "iou ii",
        "k": "kmi",
        "čka": "čke",
        "n": "nmi",
    },
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_sk = DEFAULT_RULES.apply
