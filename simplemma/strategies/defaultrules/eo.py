import re

from .generic import apply_rules

# Esperanto: strip the regular grammatical endings back to the citation form
# (-o noun, -a adjective, -i verb, -e adverb). Only the participle cells that
# clear the 99% bar reduce to the infinitive; the rest (colliding with
# lexicalized words like Esperanto) fall through to the generic cells. The
# stem floors keep unmeasured 4-5 char tokens out (monte -> *mi).
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

# invariant words whose tail matches a grammatical ending
_EXCLUDED = frozenset({"tamen", "neniu", "konstanta"})


def apply_eo(token: str) -> str | None:
    "Apply pre-defined rules for Esperanto."
    # hyphen: acronym compounds (KOVIM-19-on); caps: foreign proper nouns
    # collide with the endings (London -> *Londo)
    return apply_rules(
        token, DEFAULT_RULES, min_len=4, caps=True, hyphen=True, excluded=_EXCLUDED
    )
