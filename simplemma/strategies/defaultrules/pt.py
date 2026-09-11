from .generic import SuffixRules

# invariant words, feminine agent nouns kept as their own lemma,
# stem-extending verb forms, and lowercased proper nouns
_EXCLUDED = frozenset(
    (
        "quando vários classe comando rarará contraste software arredores hectare "
        "hectares óculos contrabando alvará trezentos pizzaria expiatórios "
        "moradora revendedora montadora investigadora passes passem variam "
        "preparam disparam fernando carlos orlando soares girolando".split()
    )
)

# Portuguese verb conjugation and noun/adjective endings, mined lemma-first
# (99.72% in-dict).
DEFAULT_RULES = SuffixRules(
    {
        "tar": "tara tá",
        "rar": "raras rara",
        "ear": "eamos earas eemos eara eeis eamo eemo eei",
        "har": "haras hara",
        "car": "quemos camos cam",
        "ar": (
            "aríamos ássemos aremos aríeis ávamos ásseis áramos areis ariam ardes"
            " asses astes assem armos áreis ávamo áramo ares arei avas ando arem"
            " aram avam arão arás asse aste ámos armo arde ávei árei ará ava ámo are"
            " ou ai"
        ),
        "zar": "zarias zaras zaria zara zá",
        "izar": "izamos izais izamo izam",
        "dor": "dores dora",
        "nar": "naras nemos nara nemo nei",
        "er": "êreis erás",
        "ir": "irdes irmos",
        "ico": "icos",
        "ção": "ções",
        "nto": "ntos",
        "smo": "smos",
        "ivo": "ivos",
        "ano": "anos",
        "ro": "ros",
        "io": "ios",
        "so": "sos",
        "lo": "los",
        "eo": "eos",
        "go": "gos",
    },
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_pt = DEFAULT_RULES.apply
