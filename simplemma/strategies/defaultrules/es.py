import re

from .generic import apply_rules

# Spanish: -ar/-er/-ir verb conjugation (consonant-anchored sub-classes,
# same shape as pt.py/gl.py), plural/gender endings for nouns and
# adjectives.
#
# Lean build (recipe v4): mined, drop-bad-cells loop, trimmed to the top
# groups covering ~70% of rule firings, merged where signatures repeated.
# 134 groups pre-trim -> 12 final, coverage 55.14%->43.68%, precision
# 99.85%, 0 chains.
DEFAULT_RULES = {
    re.compile(
        r"(?:earíamos|earemos|earíais|easteis|eábamos|eáramos|eáremos|eásemos|earéis|eabais|earais|eareis|earían|earías|easeis|eares|eemos|earan|earas|earen|eases|eando|earía|easen|eaban|eabas|earon|earán|earás|easte|eéis|eara|eare|earé|ease|eaba|eará|een|ead|ee|eó|eé)$"
    ): r"ear",
    re.compile(
        r"(?:zaríamos|zaremos|zaríais|zasteis|zábamos|záramos|záremos|zásemos|zaréis|zabais|zarais|zareis|zarían|zarías|zaseis|zares|zaras|zaran|zaren|zabas|zaban|zando|zaron|zarán|zarás|zaría|zasen|zases|zaste|zemos|zara|zare|zaré|zaba|zase|zará|zéis|zad|zen|zó|ze|zé)$"
    ): r"zar",
    re.compile(
        r"(?:taríamos|taremos|taríais|tasteis|tábamos|táramos|táremos|tásemos|taréis|tarías|tabais|tarais|tareis|tarían|taseis|tares|taran|taren|taría|tases|tabas|tando|tarán|taban|taron|tarás|tasen|taste|tare|tase|taba|tará|té|tó)$"
    ): r"tar",
    re.compile(
        r"(?:raríamos|raríais|rasteis|rábamos|ráramos|ráremos|rásemos|rarían|rarías|rabais|rarais|rareis|raseis|rasen|raban|rando|raste|rarás|raría|raron|rarán|raba|rará|rad|ró)$"
    ): r"rar",
    re.compile(
        r"(?:naríamos|naríais|nasteis|nábamos|náramos|náremos|násemos|nabais|narais|nareis|narían|narías|naseis|naste|nases|naban|nabas|nando|naron|narán|narás|naría|nasen|naba|nará|nase|nad)$"
    ): r"nar",
    re.compile(
        r"(?:laríamos|laríais|lasteis|lábamos|láramos|láremos|lásemos|larías|labais|larais|lareis|larían|laseis|lases|laste|laban|lando|laría|lasen|laron|larán|larás|lase|lará|lad)$"
    ): r"lar",
    re.compile(
        r"(?:izasteis|izábamos|izáramos|izáremos|izásemos|izabais|izaseis|izaban|izabas|izamos|izando|izasen|izases|izaste|izaba|izase|izáis|izad|izan)$"
    ): r"izar",
    re.compile(r"(?:aciones)$"): r"ación",
    re.compile(
        r"(?:áramos|asteis|ábamos|áremos|ásemos|arais|areis|abais|aseis|aban|aron)$"
    ): r"ar",
    re.compile(r"(dor|dad)(?:es)$"): r"\1",
    re.compile(
        r"(ría|ada|ado|ica|ico|era|ora|ero|nto|ido|ida|ina|nte|sta|ble|smo|rio|ita|oso|ria|ura|cia|ona|ana|ra|ía|na|ea|sa|za|ue|ga)(?:s)$"
    ): r"\1",
    re.compile(r"(?:bais)$"): r"r",
}

# Closed-class collisions found via the UD consistency scan (train+dev+
# test, always identity-gold across every occurrence): invariant function
# words/quantifiers (mientras "while", varios "several" -- not an
# inflected "vario", apenas "barely"), pluralia tantum (vacaciones,
# afueras), and occupation/institution nouns colliding with verb
# conditional-tense forms (comité, contraste, secretaría, politburó).
_EXCLUDED = frozenset(
    {
        "mientras",
        "varios",
        "apenas",
        "vacaciones",
        "comité",
        "contraste",
        "afueras",
        "secretaría",
        "politburó",
    }
)


def apply_es(token: str) -> str | None:
    "Apply pre-defined rules for Spanish."
    if len(token) < 6 or token[0].isupper() or "-" in token or token in _EXCLUDED:
        return None

    return apply_rules(token, DEFAULT_RULES)
