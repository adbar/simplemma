import re

from .generic import apply_rules

# https://en.wiktionary.org/wiki/Category:Latvian_suffixes

DEFAULT_RULES = {
    # feminine nouns
    re.compile(r"(?:ieces|iecei|iecē|ieču|iecēm|iecēs)$"): "iece",
    re.compile(r"(?:ietei|ietes|ietē|ietēm|ietēs)$"): "iete",
    re.compile(r"(?:iju|ijas|ijai|ijā)$"): "ija",
    re.compile(r"(?:ību|ības|ībai|ībā|ībām|ībās)$"): "ība",
    re.compile(r"(?:šanu|šanas|šanai)$"): "šana",
    # masculine nouns
    re.compile(r"(?:umu|uma|umam|umā|umām|umās)$"): "ums",
    re.compile(r"(?:klim|klī|kļa|kļi|kļiem|kļos|kļus)$"): "klis",
    re.compile(r"(?:nieku|nieka|niekam|niekā|nieki|niekus|niekos)$"): "nieks",
    # adjectives (this data lemmatises DEFINITE forms to the -ais form)
    re.compile(r"(?:aja|ajā|ajai|ajam|ajām|ajos|ajiem|ajās)$"): "ais",
    re.compile(r"āko$"): "ākais",
    # indefinite adjective declension -> indefinite masculine (-īgs/-isks).
    # These must precede the generic noun-case cells below, which would
    # otherwise turn feminine forms into feminine citation forms (smirdīgās
    # -> *smirdīga instead of smirdīgs) -- found via UD, invisible in-dict
    # because the feminine form is itself a real dictionary word.
    re.compile(r"(?:īgu|īga|īgam|īgi|īgus|īgiem|īgos|īgas|īgai|īgā|īgām|īgās)$"): "īgs",
    re.compile(
        r"(?:isku|iska|iskam|iskā|iski|iskus|iskiem|isko|iskos|iskai|iskas|iskām|iskās)$"
    ): "isks",
    # generic -a-stem case endings (genitive/accusative -as, locative -ā,
    # dative-plural -ām, locative-plural -ās), UD-validated as the
    # highest-value LV cells. The stem-length floors keep out the short
    # collision classes (reflexive-verb "-as" forms like "atrodas",
    # pluralia tantum like "kāzas"); the -ās lookbehinds skip reflexive
    # forms (atcerējās, atcerēšanās); definite adjectives (-ajā/-ajām/-ajās)
    # are claimed by the -ais rule above, jā- debitives by the guard below.
    re.compile(r"(.{8,})as$"): r"\1a",
    re.compile(r"(.{6,})ām$"): r"\1a",
    re.compile(r"(.{6,})(?<!j)(?<!šan)ās$"): r"\1a",
    re.compile(r"(.{7,})ā$"): r"\1a",
}

# Capitalized tokens (mostly proper nouns: place names, surnames) decline
# like nouns, so the noun-case cells apply cleanly, while the adjective
# cells would mangle names ending in adjective-like letters
# (Havajā -> *Havais).
_ADJECTIVE_TARGETS = frozenset({"ais", "ākais", "īgs", "isks"})
_PROPER_NOUN_RULES = {
    pattern: repl
    for pattern, repl in DEFAULT_RULES.items()
    if repl not in _ADJECTIVE_TARGETS
}


def apply_lv(token: str) -> str | None:
    "Apply pre-defined rules for Latvian."
    # jā- is the debitive-mood verb marker: those are verb forms whose lemma
    # is an infinitive, out of reach of these noun/adjective rules.
    if len(token) < 5 or token.startswith("jā"):
        return None

    rules = _PROPER_NOUN_RULES if token[0].isupper() else DEFAULT_RULES
    return apply_rules(token, rules)
