import re

from .generic import apply_rules

# Esperanto inflection is fully regular: strip the grammatical endings back to
# the part-of-speech citation form (-o noun, -a adjective, -i verb, -e adverb).
# Deverbal forms stop at the noun/adjective citation (kurantojn -> kuranto).
DEFAULT_RULES = {
    # nouns (incl. participial nouns): plural -j, accusative -n
    re.compile(r"(?:ojn|oj|on)$"): "o",
    # adjectives (incl. participles): plural -j, accusative -n
    re.compile(r"(?:ajn|aj|an)$"): "a",
    # verbs: present -as, past -is, future -os, conditional -us, imperative -u
    re.compile(r"(?:as|is|os|us|u)$"): "i",
    # adverbs: directional accusative -en
    re.compile(r"en$"): "e",
}


def apply_eo(token: str) -> str | None:
    "Apply pre-defined rules for Esperanto."
    if len(token) < 4:
        return None

    return apply_rules(token, DEFAULT_RULES)
