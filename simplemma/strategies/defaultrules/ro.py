from .generic import SuffixRules

# genuine collisions only (identity lemmas, participle-vs-noun homographs,
# vowel-changing plurals, irregulars); UD preferring the infinitive over the
# dict's participle lemma is a convention difference, not stoplisted
_EXCLUDED = frozenset(
    (
        "înspăimânțaseși admirăm rămaseră vreunul țările păsările flăcările destul "
        "stimul vehicul neconformitatea conduită judecată bucată turburatu "
        "endonimul stabili".split()
    )
)

# Romanian verb conjugation and noun/adjective endings (fused definite
# articles included), mined lemma-first (99.73% in-dict).
DEFAULT_RULES = SuffixRules(
    {
        "ta": "tase tai tam tăm tau tez",
        "za": "zează zară zase zași zezi zeze zau zai zam zăm zez",
        "na": "nase nau nam nai năm",
        "itate": "ităților itățile ității ități",
        "a": "aserăți aserăm aseră aseși arăți arăm asem aţi atu",
        "tor": "torule",
        "bil": "bilului bililor bilul bilii bili",
        "ație": "ațiilor ațiile ația",
        "at": "aților atule",
        "it": "iților itule",
        "or": "orului orul",
        "ic": "icului icul",
        "al": "alului alul ali",
        "os": "osul",
        "ar": "arului arul",
        "er": "erului erul",
        "iv": "ivului ivul",
        "t": "tului tul",
        "i": "irăți irăm isem iţi itu",
        "n": "nului nul",
        "ire": "irile irea ireo",
        "are": "ările",
        "m": "mului mul",
        "s": "sului",
        "izat": "izați",
        "tat": "tați tată",
        "uit": "uite uită uiți",
        "cat": "cată cați",
        "nit": "niți nită",
        "zat": "zată",
        "nat": "nați",
        "ție": "ției",
        "ate": "atea",
        "iat": "iată",
        "lat": "lați",
    },
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_ro = DEFAULT_RULES.apply
