import re

from .generic import apply_rules

# Malay possessive/pronominal enclitics: -ku (my), -mu (your), -nya (his/her/its).
# Fully regular and attach to nouns, proper nouns, and adjectives alike.
DEFAULT_RULES = {
    re.compile(r"(?:nya|ku|mu)$"): "",
}


def apply_ms(token: str) -> str | None:
    "Apply pre-defined rules for Malay."
    # short roots (baku, buku, ilmu, kamu, bangku, sesiku, ...) collide with
    # the clitics; a hyphen marks a reduplicated plural (buku-buku), whose
    # second half is not itself cliticised.
    if len(token) < 7 or "-" in token:
        return None

    return apply_rules(token, DEFAULT_RULES)
