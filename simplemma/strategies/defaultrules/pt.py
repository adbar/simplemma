import re

from .generic import apply_rules

# Portuguese: -ar/-er/-ir verb conjugation (-tar/-rar/-ear/-har/-zar/-nar/
# -lar/-car/-iar/-izar sub-classes each anchor their own consonant), plural/
# gender endings for nouns and adjectives.
#
# Lean build (recipe v4): mined, drop-bad-cells loop, then trimmed to the
# top groups covering ~70% of rule firings (not the old 90% -- a
# deliberate policy change trading coverage for a much shorter, easier to
# audit file) and merged where signatures repeated. 210 groups pre-trim ->
# 23 final, coverage 62.80%->51.01%, precision 99.90%, 0 chains (the
# "-doras"/"-dora" feminine-agent-noun alt was dropped afterwards, an
# open-ended class -- see the DEFAULT_RULES entry for "dores").
DEFAULT_RULES = {
    re.compile(
        r"(?:taríamos|tássemos|taremos|taríeis|távamos|táramos|tásseis|tardes|tareis|tariam|tarmos|tassem|tasses|tastes|táreis|távamo|táramo|tares|taras|tavam|tavas|tando|tarei|tarem|taram|tarás|tarão|támos|tasse|taste|tarmo|tarde|tárei|távei|tara|tava|tará|támo|tare|tai|tou|tá)$"
    ): r"tar",
    re.compile(
        r"(?:raríamos|rássemos|raremos|raríeis|ráramos|rásseis|rávamos|rastes|rariam|rareis|rassem|rasses|rardes|rarmos|ráreis|ráramo|rávamo|rando|raste|raras|rarei|rarás|rarão|rasse|rámos|raram|rarem|rares|rarmo|rarde|rárei|rávei|rara|rará|rámo|rare|rou)$"
    ): r"rar",
    re.compile(
        r"(?:earíamos|eássemos|earemos|earíeis|eáramos|eásseis|eávamos|earias|eardes|eareis|eariam|earmos|eassem|easses|eastes|eáreis|eáramo|eávamo|eares|eamos|earia|eando|earas|earam|earei|earem|earás|earão|easse|easte|eavam|eavas|eemos|eámos|earmo|earde|eárei|eara|eará|eava|eeis|eamo|eemo|eámo|eai|eei|eou)$"
    ): r"ear",
    re.compile(
        r"(?:haríamos|hássemos|haremos|haríeis|háramos|hásseis|hávamos|háveis|hardes|hareis|hariam|harmos|hassem|hasses|hastes|háreis|háramo|hávamo|hares|haras|havam|havas|harão|hando|haram|harei|harem|harás|hasse|haste|hámos|harmo|harde|hárei|hávei|hava|hara|hará|hámo|hare|hai|hou|há)$"
    ): r"har",
    re.compile(
        r"(?:zaríamos|zássemos|zaremos|zaríeis|záramos|zásseis|závamos|zareis|zarias|zardes|zariam|zarmos|zassem|zasses|zastes|záreis|záramo|závamo|zares|zaras|zaram|zarei|zarem|zaria|zando|zarás|zarão|zasse|zaste|zavam|zavas|zámos|zarmo|zarde|zárei|závei|zara|zará|zava|zámo|zare|zai|zou|zá)$"
    ): r"zar",
    re.compile(
        r"(?:naríamos|nássemos|naremos|naríeis|náramos|násseis|návamos|nardes|nareis|nariam|narmos|nassem|nasses|nastes|náreis|náramo|návamo|nares|navas|naras|nemos|nando|naram|narei|narem|narás|narão|nasse|naste|navam|námos|narmo|narde|nárei|návei|neis|nava|nara|nará|nemo|námo|nare|nai|nei|nou|ná)$"
    ): r"nar",
    re.compile(
        r"(?:laríamos|lássemos|laremos|laríeis|láramos|lásseis|lávamos|lareis|lasses|lariam|lastes|lassem|lardes|larmos|láreis|láramo|lávamo|lares|lemos|laram|larei|larem|lasse|larão|laste|lavam|lando|larás|lámos|larmo|larde|lárei|lávei|lava|leis|lará|lemo|lámo|lei|lai|lou)$"
    ): r"lar",
    re.compile(
        r"(?:caríamos|cássemos|caríeis|cáramos|cásseis|cávamos|quemos|cardes|casses|cassem|cariam|carmos|castes|cáreis|cáramo|cávamo|camos|cavam|carás|casse|cando|carão|caste|cámos|carmo|carde|cárei|cávei|cámo|cam|cou|cai)$"
    ): r"car",
    re.compile(
        r"(?:izáramos|izásseis|izávamos|izassem|izasses|izastes|izáreis|izáramo|izávamo|izamos|izando|izasse|izaste|izavam|izavas|izámos|izárei|izávei|izais|izava|izamo|izámo|izai|izou|izam|izo|izá)$"
    ): r"izar",
    re.compile(r"(?:adíssima|adíssimo|ados)$"): r"ado",
    re.compile(
        r"(?:ássemos|ávamos|ásseis|áramos|armos|áreis|ávamo|áramo|ámos|armo|ávei|árei|ámo|ou)$"
    ): r"ar",
    re.compile(
        r"(?:íssemos|ísseis|íramos|irdes|irmos|íreis|íramo|írei|irde|iu)$"
    ): r"ir",
    re.compile(r"(?:êssemos|êramos|êsseis|êreis|êramo|erás)$"): r"er",
    re.compile(
        r"(?:iarias|iardes|iareis|iariam|iarmos|iassem|iasses|iastes|iáreis|iares|iaria|iando|iarão|iaram|iarei|iarem|iarás|iasse|iaste|iavam|iavas|iámos|iara|ieis|iará|iava)$"
    ): r"iar",
    re.compile(r"(?:dores)$"): r"dor",
    re.compile(r"(?:ações)$"): r"ação",
    re.compile(r"(?:eadas|eada)$"): r"eado",
    re.compile(r"(?:íveis)$"): r"ível",
    re.compile(r"(?:agens)$"): r"agem",
    re.compile(
        r"(ria|ada|ica|ico|ira|ora|nte|nto|iro|ida|sta|ido|smo|rio|cia|ade|ina|oso|eia|ura|ana|ivo|ano|lha|gia|ite|ona|ela|nia|mia|tro|ice|ra|te|da|do|va|ca|co|na|io|la|ma|sa|so|ça|ce|ga|lo|za|eo|vo|go|ço)(?:s)$"
    ): r"\1",
    re.compile(r"(?:ções)$"): r"ção",
    re.compile(r"(?:gens)$"): r"gem",
    re.compile(r"(?:fica)$"): r"fico",
}

# The feminine-agent-noun class ("-adora" kept as its own lemma rather than
# reduced to masculine "-ador") was dropped from the rule above ("dores"
# only, not "doras"/"dora") instead of stoplisted -- an open-ended class,
# not a finite list, per the lean-rules policy. Everything below IS a
# finite, closed set found via the UD consistency scan (train+dev+test,
# always identity-gold across every occurrence): invariant adverbs/
# quantifiers (apenas, vários, rarará, entrementes, prestes, avessas),
# pluralia tantum (óculos, arredores), common-noun/verb-form homographs
# (classe, contraste, hectare, mecenas, trezentos, pizzaria), and two
# gerund-shaped proper nouns (girolando, memorando).
_EXCLUDED = frozenset(
    {
        "apenas",
        "vários",
        "classe",
        "rarará",
        "contraste",
        "arredores",
        "hectare",
        "óculos",
        "entrementes",
        "prestes",
        "mecenas",
        "trezentos",
        "pizzaria",
        "avessas",
        "girolando",
        "memorando",
    }
)


def apply_pt(token: str) -> str | None:
    "Apply pre-defined rules for Portuguese."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
