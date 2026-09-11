from .generic import SuffixRules

# idempotence chains (centēsimō -> centēsimo -> *centēsimus) plus one invariant
_EXCLUDED = frozenset(
    "centēsimō cinnabarim dēcantō mūsimō trānsplantō tūtissimō fortasse".split()
)

# Latin verb conjugation and noun/adjective declension, mined lemma-first
# (99.69% in-dict). min_stem=2 keeps whole-word or 1-char-stem matches from
# stripping to a bare target (abimus -> *o, antium -> *ans).
DEFAULT_RULES = SuffixRules(
    {
        "tio": "tionis tione",
        "iens": "ientis ientem ientes ienti iente",
        "o": (
            "averunt avisset averant averint avissem avisses avistis assemus"
            " assetis abitis abatis abamus abimus avisse averit averam averat averas"
            " averim avimus avisti aritis assent arimus abant abunt atote avero"
            " astis asses assem asset arunt arint anto abis abam abas abit abat avit"
            " asse asti arim arit abo ō"
        ),
        "turus": "turorum turos tūrus tūrum turi ture turo",
        "andus": "andarum andis andas andam andae anda ande",
        "ans": "antibus antium antis antem antes anti ante āns",
        "endus": "endarum endae enda",
        "io": "ionibus ionem iones ionum iōnis ioni",
        "ens": "entibus entium ēns",
        "tatus": "tata",
        "ior": "ioribus ioris iorem iores iora iore iori",
        "surus": "surorum suros sūrum sūrus sure suri suro",
        "tor": "toribus torem tores tore",
        "atus": "atarum atas atos atae atam ātus āta",
        "ndus": "ndorum ndos",
        "eo": "ebitis ebimus eamus ebunt etote eant ebit eat ebo",
        "cens": "centis centi",
        "dens": "dentis",
        "simus": "simae simam simas simis simos sima simo simi",
        "tas": "tatem tates tātis tās",
        "co": "camus cant cat",
        "to": "tamus tant tat",
        "nsis": "nsium nsia",
        "ensis": "ēnsis",
        "urus": "urum",
        "or": "ōris",
        "icus": "icos",
        "bilis": "bile",
        "rius": "rios",
        "ctus": "ctos",
        "itus": "itos",
        "ratus": "rati",
    },
    min_stem=2,
    min_len=6,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_la = DEFAULT_RULES.apply
