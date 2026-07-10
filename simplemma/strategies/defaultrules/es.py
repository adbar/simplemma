import re

from .generic import apply_rules

# Spanish verb conjugation and noun/adjective plural endings, mined
# lemma-first (99.81% in-dict).
DEFAULT_RULES = {
    re.compile(
        r"(?:earíamos|earemos|earíais|easteis|eábamos|eáramos|eáremos|eásemos"
        r"|earéis|eabais|earais|eareis|earían|earías|easeis|eares|eemos|earan"
        r"|earas|earen|eases|eando|earía|easen|eaban|eabas|earon|earán|earás"
        r"|easte|eéis|eara|eare|earé|ease|eaba|eará|een|ead|ee|eó|eé)$"
    ): r"ear",
    re.compile(
        r"(?:zaríamos|zaremos|zaríais|zasteis|zábamos|záramos|záremos|zásemos"
        r"|zaréis|zabais|zarais|zareis|zarían|zarías|zaseis|zares|zaran|zaren"
        r"|zabas|zaban|zando|zaron|zarán|zarás|zaría|zasen|zases|zaste|zemos"
        r"|zara|zare|zaré|zaba|zase|zará|zéis|zad|zen|zó|ze|zé)$"
    ): r"zar",
    re.compile(
        r"(?:taríamos|taríais|tasteis|tábamos|táramos|táremos|tásemos|tarías"
        r"|tabais|tarais|tareis|tarían|taseis|taría|tases|tabas|tando|tarán"
        r"|taban|taron|tarás|tasen|taste|tare|tase|taba|tará|té|tó)$"
    ): r"tar",
    re.compile(
        r"(?:naríamos|naríais|nasteis|nábamos|náramos|náremos|násemos|nabais"
        r"|narais|nareis|narían|narías|naseis|naste|nases|naban|nabas|nando"
        r"|naron|narán|narás|naría|nasen|naba|nará|nase|nad|nó)$"
    ): r"nar",
    re.compile(
        r"(?:laríamos|laríais|lasteis|lábamos|láramos|láremos|lásemos|larías"
        r"|labais|larais|lareis|larían|laseis|lases|laste|laban|lando|laría"
        r"|lasen|laron|larán|larás|lase|lará|lad)$"
    ): r"lar",
    re.compile(
        r"(?:caríamos|caríais|casteis|cábamos|cáramos|cáremos|cásemos|carías"
        r"|cabais|carais|careis|carían|caseis|caban|cabas|cases|caste|casen"
        r"|carás|cando|caría|caron|carán|quéis|caba|cará|cad|có)$"
    ): r"car",
    re.compile(
        r"(?:iaríamos|iaríais|iasteis|iábamos|iáramos|iáremos|iásemos|iabais"
        r"|iarais|iareis|iarían|iarías|iaseis|iaban|iabas|iando|iaron|iarán"
        r"|iarás|iaría|iasen|iases|iaste|iemos|iaba|iará|iase|iéis|iad|ien"
        r"|ian)$"
    ): r"iar",
    re.compile(
        r"(?:garíamos|garíais|gasteis|gábamos|gáramos|gáremos|gásemos|garías"
        r"|gabais|garais|gareis|garían|gaseis|garía|gaban|gabas|gando|garon"
        r"|garán|garás|gasen|gaba|gará|gad)$"
    ): r"gar",
    re.compile(
        r"(?:daríamos|daríais|dasteis|dábamos|dáramos|dáremos|dásemos|dabais"
        r"|darais|dareis|darían|darías|daseis|dabas|dando|daban|daron|darán"
        r"|darás|daría|dasen|dases|daba|daré|dará)$"
    ): r"dar",
    re.compile(r"(?:aciones)$"): r"ación",
    re.compile(r"(?:izamos|izáis|izan|izes)$"): r"izar",
    re.compile(r"(?:onamos|onáis|onan)$"): r"onar",
    re.compile(r"(?:dores)$"): r"dor",
    re.compile(r"(?:dades)$"): r"dad",
    re.compile(r"(?:icos)$"): r"ico",
    re.compile(r"(?:eros)$"): r"ero",
    re.compile(r"(?:ntos)$"): r"nto",
    re.compile(r"(?:smos)$"): r"smo",
    re.compile(r"(?:rios)$"): r"rio",
    re.compile(r"(?:osos)$"): r"oso",
    re.compile(r"(?:ivos)$"): r"ivo",
    re.compile(r"(?:inos)$"): r"ino",
    re.compile(r"(?:enos)$"): r"eno",
    re.compile(r"(?:gos)$"): r"go",
}

# invariant words, no-accent variants colliding with the -iar cell, the
# -eer verb class vs -ear endings, and lowercased proper nouns
_EXCLUDED = frozenset(
    {
        "varios",
        "alguien",
        "vacaciones",
        "comité",
        "secretaría",
        "buenos",
        "clases",
        "tambien",
        "recien",
        "tenian",
        "decian",
        "deberian",
        "querian",
        "christian",
        "creemos",
        "provee",
        "poseen",
        "fernando",
        "orlando",
        "itelmenos",
    }
)


def apply_es(token: str) -> str | None:
    "Apply pre-defined rules for Spanish."
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
