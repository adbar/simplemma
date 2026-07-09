import re

from .generic import apply_rules

# Esperanto inflection is fully regular: strip the grammatical endings back to
# the part-of-speech citation form (-o noun, -a adjective, -i verb, -e adverb).
# Participles reduce to the verb infinitive per the dictionary's convention
# (kurantojn -> kuri), but only 9 of the 54 (series x ending) cells clear the
# 99% bar -- the "-e" adverb forms plus the active-series bare "-a"; the rest
# collide with lexicalized non-participle words (diamanto, Esperanto) and fall
# through to the generic cells below. The stem floors keep unmeasured 4-5
# char tokens out (monte -> *mi).
DEFAULT_RULES = {
    re.compile(r"(.{2,})(?:ante|inte|onte)$"): r"\1i",
    re.compile(r"(.{3,})(?:ate|ite|ote)$"): r"\1i",
    re.compile(r"(.{2,})(?:anta|inta|onta)$"): r"\1i",
    # nouns: plural -j, accusative -n
    re.compile(r"(?:ojn|oj|on)$"): "o",
    # adjectives: plural -j, accusative -n
    re.compile(r"(?:ajn|aj|an)$"): "a",
    # verbs: present -as, past -is, future -os, conditional -us, imperative -u
    re.compile(r"(?:as|is|os|us|u)$"): "i",
    # adverbs: directional accusative -en
    re.compile(r"en$"): "e",
}

# invariant words whose tail matches a grammatical ending: tamen (however),
# neniu (nobody), konstanta (lexicalized adjective, no verb *konsti).
_EXCLUDED = frozenset({"tamen", "neniu", "konstanta"})


def apply_eo(token: str) -> str | None:
    "Apply pre-defined rules for Esperanto."
    # hyphenated tokens are dominated by acronym compounds (KOVIM-19-on)
    # the suffix rules mishandle -- skip. caps=True (as every other module):
    # capitalized foreign proper nouns collide with the endings (London -> *Londo).
    return apply_rules(
        token, DEFAULT_RULES, min_len=4, caps=True, hyphen=True, excluded=_EXCLUDED
    )
