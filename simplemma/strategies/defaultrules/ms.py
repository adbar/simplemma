import re

from .generic import apply_rules

# Malay possessive/pronominal enclitics: -ku, -mu, -nya.
DEFAULT_RULES = {
    re.compile(r"(?:nya|ku|mu)$"): "",
}


def apply_ms(token: str) -> str | None:
    "Apply pre-defined rules for Malay."
    # short roots (baku, kamu, ...) collide with the clitics; a hyphen
    # marks a reduplicated plural (buku-buku)
    return apply_rules(token, DEFAULT_RULES, min_len=7, hyphen=True)
