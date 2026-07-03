import re

from .generic import apply_rules

# Swedish: noun declension (definite singular -en/-et, definite plural -na/
# -rna/-erna, plural -ar/-or/-er), adjective declension and comparison
# (-are/-ast, -a/-t/-are agreement), and verb conjugation (-ar/-er/-de/-t
# groups). Several bare/short alternatives were dropped after the combined-
# ruleset check: they either collide with -ens/-ans French-loanword nouns
# whose citation form already ends in -s (abstinens, konsonans), or with
# specific compounds where the root coincidentally ends like an inflected
# form (numerus -> numersen would otherwise strip as if genitive).
# Trimmed to the top rule groups covering ~90% of rule firings.
# Stem classes sharing one ending paradigm are merged into single
# capture-group rules ((x|y)endings$ -> \1...), verified output-identical
# to the unmerged form over the full dictionary.
DEFAULT_RULES = {
    re.compile(r"(?:ingarnas|ingarna|ingars|ingens|ingar|ingen|ings)$"): r"ing",
    re.compile(
        r"(bar|lig|sig|tig|dig|tiv|ell|kig|ig)(?:astes|ares|aste|asts|are|ast|es|as|ts|e|a|s|t)$"
    ): r"\1",
    re.compile(r"(het|ion|tet|ism|nad|tur)(?:ernas|erna|ens|ers|en|er|s)$"): r"\1",
    re.compile(
        r"(?:iskastes|iskares|iskaste|iskasts|iskare|iskast|iskts|isks|iskt)$"
    ): r"isk",
    re.compile(r"(tor|or)(?:ernas|erna|ers|er|s)$"): r"\1",
    re.compile(
        r"(?:rigastes|rigaste|rigasts|rigast|rigas|riges|rigts|rigs|riga|rige|rigt)$"
    ): r"rig",
    re.compile(
        r"(?:nskastes|nskares|nskaste|nskasts|nskare|nskast|nskes|nskts|nsks|nskt)$"
    ): r"nsk",
    re.compile(
        r"(?:lösastes|lösares|lösaste|lösasts|lösare|lösast|lösas|löses|lösa|löse)$"
    ): r"lös",
    re.compile(
        r"(?:sammares|sammaste|sammasts|sammare|sammast|samts|sams|samt)$"
    ): r"sam",
    re.compile(r"(?:arastes|arares|araste|arasts|arare|arast|arens|aren|ars)$"): r"ar",
    re.compile(r"(?:skastes|skaste|skasts|skts|sks|skt)$"): r"sk",
    re.compile(r"(?:adernas|aderna|aden|ads)$"): r"ad",
    re.compile(r"(kt|al)(?:astes|ernas|aste|erna|asts|ast)$"): r"\1",
    re.compile(r"(?:ntastes|ntares|ntaste|ntasts|ntare|ntast|nts)$"): r"nt",
    re.compile(r"(ck|tt)(?:ornas|orna|ors|ans|as|an|or)$"): r"\1a",
    re.compile(
        r"(?:ärernas|ärastes|ärerna|äraste|ärasts|ärens|ärers|ärast|ären|ärer|äres|ärs)$"
    ): r"är",
    re.compile(r"(?:aternas|aterna|atens|atets|aten|atet)$"): r"at",
    re.compile(r"(?:nsernas|nserna|nsens|nsers|nsen|nser)$"): r"ns",
    re.compile(r"(?:ddastes|ddaste|ddasts|ddast|ddas|dds|dda)$"): r"dd",
    re.compile(r"(?:anernas|anerna|anens|anen)$"): r"an",
    re.compile(r"(rd|g)(?:astes|aste|asts|ast|s)$"): r"\1",
    re.compile(r"(?:mannens|männens|mannen|männen|mans)$"): r"man",
    re.compile(r"(?:ldastes|ldernas|ldaste|ldasts|lderna|ldast|lds)$"): r"ld",
    re.compile(r"(t|d)(?:astes|asts|aste|ast)$"): r"\1",
    re.compile(r"(nde|ier)(?:nas|na|s)$"): r"\1",
    re.compile(r"(?:ternas|ters)$"): r"ter",
    re.compile(r"(?:dernas|derna|drets|ders|dret)$"): r"der",
    re.compile(r"(?:ratens|raten|rats)$"): r"rat",
    re.compile(r"(?:tornas|torna|tas)$"): r"ta",
    re.compile(r"(?:erande|eras)$"): r"era",
    re.compile(r"(?:kernas|kerna|kerns|kers|kern)$"): r"ker",
    re.compile(r"(?:éernas|éerna|éers|éer|éns|én|és)$"): r"é",
    re.compile(r"(tal|ål)(?:ens|ets|et|en|s)$"): r"\1",
    re.compile(r"(?:ernas|erna)$"): r"er",
    re.compile(r"(?:elets|elns|elet|els|eln)$"): r"el",
    re.compile(r"(?:skans|skas|skan)$"): r"ska",
    re.compile(r"(?:rnens|rnen|rns)$"): r"rn",
    re.compile(r"(are|gen|ken|st|et|da)(?:s)$"): r"\1",
    re.compile(r"(?:inen|ins)$"): r"in",
    re.compile(r"(?:nas|nan)$"): r"na",
}

# closed set of compounds whose root ends in "-anter"/"-lanter", which looks
# like the -er indefinite plural of an -ant agent noun (lantern is unrelated
# to any -ant word); plus invariant adverbs/conjunctions/prepositions whose
# tail happens to match a declension/conjugation ending (UD validation,
# 2026-07 -- e.g. "enligt" was being stripped to "enlig" by the -ig
# adjective-comparison rule).
_EXCLUDED = frozenset(
    {
        "lanterna",
        "lanternas",
        "sidolanterna",
        "sidolanternas",
        "topplanterna",
        "topplanternas",
        "enligt",
        "tillsammans",
        "endast",
        "antingen",
        "enbart",
        "annars",
        "dessförinnan",
        "respektive",
    }
)


def apply_sv(token: str) -> str | None:
    "Apply pre-defined rules for Swedish."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
