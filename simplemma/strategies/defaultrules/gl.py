import re

from .generic import apply_rules

# Galician: -ar/-er/-ir verb conjugation (consonant-anchored sub-classes,
# same shape as pt.py), plural/gender endings for nouns and adjectives.
#
# Lean build (recipe v4): mined, drop-bad-cells loop, trimmed to the top
# groups covering ~80% of rule firings, merged where signatures repeated.
# 136 groups pre-trim -> 18 final, coverage 61.86%->51.17%, precision
# 99.87%, 0 chains.
DEFAULT_RULES = {
    re.compile(
        r"(?:lariades|lariamos|larades|laredes|laremos|labades|labamos|lásedes|laramos|lásemos|lastes|laches|lardes|larías|larían|larmos|lares|laras|laran|larei|laren|laban|laría|lasen|lando|laron|larán|larás|lara|lase|lade|lará|lou|lei)$"
    ): r"lar",
    re.compile(
        r"(?:tariades|tariamos|tabades|tabamos|taredes|taremos|tarades|tásedes|taramos|tásemos|tarías|taches|tardes|tarían|tastes|tarmos|tares|taría|tabas|tando|taban|tarei|taren|tarán|tarás|taran|taron|tasen|taba|tará|tou|tei)$"
    ): r"tar",
    re.compile(
        r"(?:zariades|zariamos|zabades|zabamos|zarades|zaredes|zaremos|zásedes|zaramos|zásemos|zaches|zardes|zarían|zarías|zastes|zarmos|zaras|zares|zaban|zabas|zando|zaran|zarei|zaren|zaron|zarán|zarás|zaría|zasen|zases|zade|zara|zaba|zará|zase|cei|zou)$"
    ): r"zar",
    re.compile(
        r"(?:cariades|cariamos|cabades|cabamos|carades|caredes|caremos|caramos|cásedes|cásemos|castes|caches|carías|quedes|cardes|carían|quemos|carmos|cares|cases|caban|cabas|camos|caran|carei|caren|casen|carás|cando|caría|caron|carán|cade|case|caba|cará|quen|quei|can|cou)$"
    ): r"car",
    re.compile(
        r"(?:eariades|eariamos|eabades|eabamos|earades|earedes|earemos|eásedes|earamos|eásemos|eaches|eardes|earían|earías|eastes|earmos|eares|eades|eamos|eases|earas|eaban|eabas|eando|earan|earei|earen|earon|earán|earás|earía|easen|eedes|eemos|ease|eaba|eade|eara|eará|ean|ees|eei|een|eou|ee)$"
    ): r"ear",
    re.compile(
        r"(?:rariades|rariamos|rarades|raramos|raredes|raremos|rásedes|rásemos|rarías|rastes|raches|rardes|rarmos|rarían|rasen|rares|raría|raran|raras|rarei|raren|raron|rarán|rarás|rara|rará|rou)$"
    ): r"rar",
    re.compile(
        r"(?:nariades|nariamos|narades|naredes|naremos|nabades|nabamos|naramos|násedes|násemos|narías|naches|nardes|narían|nastes|narmos|nares|naras|naría|nases|naran|narei|naren|nasen|naban|nabas|nando|naron|narán|narás|nedes|nemos|nade|nara|naba|nará|nase|nei|nou)$"
    ): r"nar",
    re.compile(
        r"(?:izabades|izabamos|izásedes|izásemos|izaches|izastes|izades|icedes|icemos|izamos|izaban|izabas|izando|izasen|izases|izade|izaba|izase|icen|izan|icei|izou)$"
    ): r"izar",
    re.compile(r"(?:ándodes|abades|abamos|ásedes|ásemos|armos|aban|aron|ou)$"): r"ar",
    re.compile(r"(?:ésedes|ésemos|eron|erán|erás|erá)$"): r"er",
    re.compile(r"(?:irdes|irmos|iron|iu)$"): r"ir",
    re.compile(r"(dor|gar)(?:es)$"): r"\1",
    re.compile(r"(?:ábeis)$"): r"ábel",
    re.compile(
        r"(ría|ada|ado|ión|ica|ico|ira|nte|iro|ido|ble|smo|nto|sta|rio|ina|oso|cia|ria|ide|ura|lla|ivo|ano|ita|ela|ra|ía|da|do|ón|ca|ta|co|ro|ia|to|na|la|io|sa|za|lo|ue|no|so|ea|ga|ma|vo|ña|xe|go|me|eo|a|n)(?:s)$"
    ): r"\1",
    re.compile(r"(?:beis)$"): r"bel",
    re.compile(r"(r|)(?:on)$"): r"\1",
    re.compile(r"(?:eis)$"): r"el",
    re.compile(r"(?:ais)$"): r"al",
}

# párkinson (loanword): "-on"->"" strips it to "párkins", which then
# matches "-s"->"" again -- both rules are independently correct for
# regular words, just not idempotent on this specific loanword. Most of
# the rest found via the UD consistency scan on gl_treegal (general-domain;
# gl_ctg's own scan gives ~60 hits, almost all castellanized technical
# vocabulary absent from both treebank and dictionary in singular form
# too -- a domain-mismatch artifact, not a rules signal, see
# morphological-rules-review notes): invariant adverbs (ademais, demais,
# denantes, apenas, quizais), varios (quantifier, not an inflected
# "vario"), patróns and beiras (pluralia tantum), catrocentos (a number
# word), hostalaría/infantaría (occupation nouns colliding with a verb
# conditional form), cervantes (surname colliding with the agent-noun
# rule).
_EXCLUDED = frozenset(
    {
        "párkinson",
        "ademais",
        "varios",
        "demais",
        "denantes",
        "patróns",
        "apenas",
        "beiras",
        "catrocentos",
        "hostalaría",
        "infantaría",
        "cervantes",
        "quizais",
    }
)


def apply_gl(token: str) -> str | None:
    "Apply pre-defined rules for Galician."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
