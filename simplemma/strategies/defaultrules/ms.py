from .generic import SuffixRules

# Malay possessive/pronominal enclitics: -ku, -mu, -nya.
# short roots (baku, kamu, ...) collide with the clitics
DEFAULT_RULES = SuffixRules(
    {
        "": "nya ku mu",
    },
    min_len=7,
)


apply_ms = DEFAULT_RULES.apply
