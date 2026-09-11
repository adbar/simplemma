from .generic import SuffixRules

# invariant words whose tail matches a grammatical ending
_EXCLUDED = frozenset({"tamen", "neniu", "konstanta"})

# Esperanto: strip the regular grammatical endings back to the citation form
# (-o noun, -a adjective, -i verb, -e adverb). Only the participle cells that
# clear the 99% bar reduce to the infinitive; the rest (colliding with
# lexicalized words like Esperanto) fall through to the generic cells. The
# stem floors keep unmeasured 4-5 char tokens out (monte -> *mi).
# hyphen: acronym compounds (KOVIM-19-on); caps: foreign proper nouns
# collide with the endings (London -> *Londo)
DEFAULT_RULES = SuffixRules(
    {
        # verbs -as/-is/-os/-us/-u; participles need a 2-3 char stem
        "i": "..ante ..inte ..onte ...ate ...ite ...ote ..anta ..inta ..onta as is os us u",
        # nouns: plural -j, accusative -n
        "o": "ojn oj on",
        # adjectives: plural -j, accusative -n
        "a": "ajn aj an",
        # adverbs: directional accusative -en
        "e": "en",
    },
    min_len=4,
    caps=True,
    hyphen=True,
    excluded=_EXCLUDED,
)


apply_eo = DEFAULT_RULES.apply
