from .generic import SuffixRules

# Malay possessive/pronominal enclitics: -ku, -mu, -nya.
# short roots (baku, kamu, ...) collide with the clitics; a hyphen
# marks a reduplicated plural (buku-buku)
DEFAULT_RULES = SuffixRules(
    {
        "": "nya ku mu",
    },
    min_len=7,
    hyphen=True,
)


apply_ms = DEFAULT_RULES.apply
