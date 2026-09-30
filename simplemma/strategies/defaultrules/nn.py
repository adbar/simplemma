from .generic import SuffixRules

_EXCLUDED = frozenset(
    "erfaren helsefaren herskaren hærskaren klaren saumfaren skaren staren "
    "uerfaren rasfaren medfaren spreidningsfaren gaaren vegstandaren farane "
    "harane helsefarane herskarane hærskarane klarane skarane starane "
    "forrædarane jegarane berlinbuarane kosovoalbanarane "
    "tvinga betinga springa svingar umyndiggjøringen".split()
)

# no -arar cell on purpose: it collides with -a verb presents
DEFAULT_RULES = SuffixRules(
    {
        "ing": "ingane ingar ingen inga",
        "ar": "arane aren",
        "jon": "jonane jonar jonen",
        "isk": "iske",
        "nar": "narane narar naren",
        "a": "aene aen aer",
        "g": "gaste gare",
        "ikk": "ikken",
    },
    min_len=6,
    caps=True,
    excluded=_EXCLUDED,
)


apply_nn = DEFAULT_RULES.apply
