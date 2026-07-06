import re

from .generic import apply_rules

# Norwegian Nynorsk: -ing nominalizations, -ar agent nouns, -isk adjectives,
# borrowed suffix families (-jon, -nar), definite/plural declension.
# "-arar" was dropped: it collides with the open class of -a verb presents
# (svarar) and its real-text value (33 tokens) is under the keep bar.
# "-aren"/"-arane" kept: their collisions are a finite set of -are nouns,
# stoplisted below.
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
        # -ing cells vs -a verb infinitives whose stem ends -ing
        # (tvinga -> tvinge), plus one identity-gold noun
        "tvinga",
        "betinga",
        "springa",
        "svingar",
        "umyndiggjøringen",
    }
)


def apply_nn(token: str) -> str | None:
    "Apply pre-defined rules for Norwegian Nynorsk."
    # hyphenated compounds are mostly lowercased proper-noun heads
    # (Hardanger-ordførar): 84.7% on real text, under the bar -- skip.
    return apply_rules(
        token, DEFAULT_RULES, min_len=6, caps=True, hyphen=True, excluded=_EXCLUDED
    )
