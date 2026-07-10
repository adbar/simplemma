import re

from .generic import apply_rules

# Norwegian Nynorsk noun/adjective declension. "-arar" dropped (collides with
# the open class of -a verb presents); "-aren"/"-arane" kept, their finite
# -are noun collisions stoplisted below.
DEFAULT_RULES = {
    re.compile(r"(?:ingane|ingar|ingen|inga)$"): "ing",
    re.compile(r"(?:arane|aren)$"): "ar",
    re.compile(r"(?:jonane|jonar|jonen)$"): "jon",
    re.compile(r"(?:iske)$"): "isk",
    re.compile(r"(?:narane|narar|naren)$"): "nar",
    re.compile(r"(?:aene|aen|aer)$"): "a",
    re.compile(r"(?:gaste|gare)$"): "g",
    re.compile(r"(?:ikken)$"): "ikk",
}

_EXCLUDED = frozenset(
    {
        "erfaren",
        "helsefaren",
        "herskaren",
        "hærskaren",
        "klaren",
        "saumfaren",
        "skaren",
        "staren",
        "uerfaren",
        "rasfaren",
        "medfaren",
        "spreidningsfaren",
        "gaaren",
        "vegstandaren",
        "farane",
        "harane",
        "helsefarane",
        "herskarane",
        "hærskarane",
        "klarane",
        "skarane",
        "starane",
        "forrædarane",
        "jegarane",
        "berlinbuarane",
        "kosovoalbanarane",
        # -ing cells vs -a verb infinitives (tvinga -> tvinge)
        "tvinga",
        "betinga",
        "springa",
        "svingar",
        "umyndiggjøringen",
    }
)


def apply_nn(token: str) -> str | None:
    "Apply pre-defined rules for Norwegian Nynorsk."
    # hyphenated compounds are mostly proper-noun heads -- skip
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
