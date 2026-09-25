from .generic import SuffixRules

# invariant words, no-accent variants colliding with the -iar cell, the
# -eer verb class vs -ear endings, and lowercased proper nouns
_EXCLUDED = frozenset(
    (
        "varios alguien vacaciones comité secretaría buenos clases tambien recien "
        "tenian decian deberian querian christian creemos provee poseen fernando "
        "orlando itelmenos".split()
    )
)

# Spanish verb conjugation and noun/adjective plural endings, mined
# lemma-first (99.80% in-dict). -té dropped (98.3%: acometé is -er). -gos and
# -ntos kept under 99%: they fix OOV plurals on UD train.
DEFAULT_RULES = SuffixRules(
    {
        "ear": (
            "earíamos earemos earíais easteis eábamos eáramos eáremos eásemos"
            " earéis eabais earais eareis earían earías easeis eares eemos earan"
            " earas earen eases eando earía easen eaban eabas earon earán earás"
            " easte eéis eara eare earé ease eaba eará een ead ee eó eé"
        ),
        "zar": (
            "zaríamos zaremos zaríais zasteis zábamos záramos záremos zásemos"
            " zaréis zabais zarais zareis zarían zarías zaseis zares zaran zaren"
            " zabas zaban zando zaron zarán zarás zaría zasen zases zaste zemos zara"
            " zare zaré zaba zase zará zéis zad zen zó ze zé"
        ),
        "tar": (
            "taríamos taríais tasteis tábamos táramos táremos tásemos tarías tabais"
            " tarais tareis tarían taseis taría tases tabas tando tarán taban taron"
            " tarás tasen taste tare tase taba tará tó"
        ),
        "nar": (
            "naríamos naríais nasteis nábamos náramos náremos násemos nabais narais"
            " nareis narían narías naseis naste nases naban nabas nando naron narán"
            " narás naría nasen naba nará nase nad nó"
        ),
        "lar": (
            "laríamos laríais lasteis lábamos láramos láremos lásemos larías labais"
            " larais lareis larían laseis lases laste laban lando laría lasen laron"
            " larán larás lase lará lad"
        ),
        "car": (
            "caríamos caríais casteis cábamos cáramos cáremos cásemos carías cabais"
            " carais careis carían caseis caban cabas cases caste casen carás cando"
            " caría caron carán quéis caba cará cad có"
        ),
        "iar": (
            "iaríamos iaríais iasteis iábamos iáramos iáremos iásemos iabais iarais"
            " iareis iarían iarías iaseis iaban iabas iando iaron iarán iarás iaría"
            " iasen iases iaste iemos iaba iará iase iéis iad ien ian"
        ),
        "gar": (
            "garíamos garíais gasteis gábamos gáramos gáremos gásemos garías gabais"
            " garais gareis garían gaseis garía gaban gabas gando garon garán garás"
            " gasen gaba gará gad"
        ),
        "dar": (
            "daríamos daríais dasteis dábamos dáramos dáremos dásemos dabais darais"
            " dareis darían darías daseis dabas dando daban daron darán darás daría"
            " dasen dases daba daré dará"
        ),
        "ación": "aciones",
        "izar": "izamos izáis izan izes",
        "onar": "onamos onáis onan",
        "dor": "dores",
        "dad": "dades",
        "ico": "icos",
        "ero": "eros",
        "nto": "ntos",
        "smo": "smos",
        "rio": "rios",
        "oso": "osos",
        "ivo": "ivos",
        "ino": "inos",
        "eno": "enos",
        "go": "gos",
    },
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_es = DEFAULT_RULES.apply
