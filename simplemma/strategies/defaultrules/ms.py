import re


# Malay possessive/pronominal enclitics: -ku, -mu, -nya.
DEFAULT_RULES = {
    re.compile(r"(?:nya|ku|mu)$"): "",
}
