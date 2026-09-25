from .generic import SuffixRules

# finite -are noun collisions with the -aren/-arane cells, then -ing cells vs
# -a verb infinitives (tvinga -> tvinge)
_EXCLUDED = frozenset(
    "erfaren helsefaren herskaren hærskaren klaren saumfaren skaren staren "
    "uerfaren rasfaren medfaren spreidningsfaren gaaren vegstandaren farane "
    "harane helsefarane herskarane hærskarane klarane skarane starane "
    "forrædarane jegarane berlinbuarane kosovoalbanarane "
    "tvinga betinga springa svingar umyndiggjøringen".split()
)

# Norwegian Nynorsk noun/adjective declension. "-arar" dropped (collides with
# the open class of -a verb presents); "-aren"/"-arane" kept, their finite
# -are noun collisions stoplisted below.
# hyphenated compounds are mostly proper-noun heads -- skip
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
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_nn = DEFAULT_RULES.apply
