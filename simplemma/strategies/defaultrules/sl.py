import re

from .generic import apply_rules

# Slovenian: adjective declension (-ven/-alen/-jen/-ski/-ovit families) and
# a handful of noun suffixes.
#
# 4 alternatives (eno, kim, kimi, ske) were dropped via the automated
# drop-bad-cells loop.
DEFAULT_RULES = {
    re.compile(r"(?:jenega|jenimi|jenem|jenih|jenim|jena|jene|jeni|jeno)$"): r"jen",
    re.compile(r"(?:nskega|nskem|nske|nska|nsko)$"): r"nski",
    re.compile(r"(?:alnega|alnih|alna|alne|alni|alno)$"): r"alen",
    re.compile(r"(?:jskega|jskem|jske|jsko)$"): r"jski",
    re.compile(r"(?:itvijo|itve|itvi)$"): r"itev",
    re.compile(r"(?:skega|skemu|skima|skimi|skih|skem|skim|sko)$"): r"ski",
    re.compile(r"(?:enega|enemu|enimi|enih)$"): r"en",
    re.compile(r"(?:njema|njem|nju)$"): r"nje",
    re.compile(r"(?:tnega|tnih|tnim|tne|tni|tna)$"): r"ten",
    re.compile(r"(?:nikom|nikov|niki|niku)$"): r"nik",
    re.compile(r"(?:anega|anemu|animi|anih)$"): r"an",
    re.compile(r"(?:anjih|anju)$"): r"anje",
    re.compile(r"(?:čnega|čnih|čni)$"): r"čen",
    re.compile(r"(?:ostih|ostim|ostjo|ostmi)$"): r"ost",
    re.compile(r"(?:škega|ških|škem|ško)$"): r"ški",
    re.compile(r"(?:tvijo|tvi|tve)$"): r"tev",
    re.compile(r"(?:vnega|vnih|vno)$"): r"ven",
    re.compile(r"(?:ičnih|ični)$"): r"ičen",
    re.compile(r"(?:ovemu|ovimi)$"): r"ov",
    re.compile(r"(?:ovala|ovali)$"): r"ovati",
    re.compile(r"(?:irajo)$"): r"irati",
    re.compile(r"(?:ranih)$"): r"ran",
    re.compile(r"(?:kega|kemu|kima|kem)$"): r"ki",
    re.compile(r"(?:ajmo|ajta|ajte|ajva)$"): r"ati",
    re.compile(r"(?:jajo|jala|jale|jali|jamo|jata|jal)$"): r"jati",
    re.compile(r"(?:ikih|ikom|ikov|iku)$"): r"ik",
    re.compile(r"(?:nico|nice|nici|nic)$"): r"nica",
    re.compile(r"(?:cije|cijo|ciji)$"): r"cija",
    re.compile(r"(?:stjo|stmi)$"): r"st",
    re.compile(r"(?:nili|nil)$"): r"niti",
    re.compile(r"(?:rska|rske|rsko)$"): r"rski",
    re.compile(r"(?:dnih|dni|dna)$"): r"den",
    re.compile(r"(?:kami)$"): r"ka",
    re.compile(r"(?:stva)$"): r"stvo",
    re.compile(r"(?:lcev)$"): r"lec",
    re.compile(r"(?:enju)$"): r"enje",
    re.compile(r"(?:arji)$"): r"ar",
    re.compile(r"(?:vajo)$"): r"vati",
    re.compile(r"(?:alci)$"): r"alec",
    re.compile(r"(?:jive)$"): r"jiv",
    re.compile(r"(?:ici|ico)$"): r"ica",
    re.compile(r"(?:tjo|tmi)$"): r"t",
    re.compile(r"(?:tva|tvu)$"): r"tvo",
    re.compile(r"(?:nah)$"): r"na",
    re.compile(r"(?:co)$"): r"ca",
}

# Closed-class collisions found via UD validation: a recurring STRUCTURAL
# pattern -- Slovenian adverbs derived from adjectives share the exact
# neuter-singular "-no"/"-o" case ending (totalno "totally" == the neuter
# form of totalen "total"), and UD keeps the adverb as its own lemma while
# our declension rules correctly reduce the (far more common) adjective
# case form. Not a finite class; more will likely need adding. A few
# unrelated noun/adjective homographs (vodikov, ogljikov, počitnice) are
# also listed.
_EXCLUDED = frozenset(
    {
        "nedavno",
        "potemtakem",
        "totalno",
        "počitnice",
        "premišljeno",
        "neusmiljeno",
        "potencialno",
        "vodikov",
        "utemeljeno",
        "oblikovno",
        "vrhunsko",
        "brutalno",
        "poenostavljeno",
        "hladnokrvno",
        "definitivno",
        "prizadevno",
        "objektivno",
        "rezultatsko",
        "ogljikov",
        "rutinsko",
        "biogenetsko",
        "epiduralno",
        "redakcijsko",
        "sistematsko",
        "eventualno",
        "progresivno",
    }
)


def apply_sl(token: str) -> str | None:
    "Apply pre-defined rules for Slovenian."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
