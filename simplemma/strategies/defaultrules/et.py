from .generic import SuffixRules

# Pruned to the cells that hold >=99%: short elative/illative forms collide
# with plain nouns and the -dus paradigm with -dune adjectives.

# hyphenated-compound gold uses morpheme markers suffix rules can't reproduce
DEFAULT_RULES = SuffixRules(
    {
        # adjectives -line https://en.wiktionary.org/wiki/-line
        "line": "lisesse lisest liselt lisele lisil lisel lises lised lisi lise",
        "lik": "likest",
        "dus": "duses",
        # partitive -ilist only with >=5 stem chars (short collisions: detailist)
        "iline": ".....ilist iliste",
        "amine": "amist",
        # verbal nouns -mine https://en.wiktionary.org/wiki/-mine
        "mine": (
            "mistesse misteta mistest misteni mistena mistelt mistele misteks"
            " mistega misesse mistes mistel miseta misest miseni misena miselt"
            " misele miseks miste mises misel mised mise"
        ),
        # -lik/-nik nouns https://en.wiktionary.org/wiki/-lik
        "ik": (
            "ikkudele ikkudel ikuta ikuni ikuna ikult ikule ikuks ikuga iketa ikeni"
            " ikena ikelt ikele ikeks ikul ikud ikku ikke iku"
        ),
        # -kond nouns https://en.wiktionary.org/wiki/-kond
        "kond": (
            "kondadesse kondadest kondadelt kondadele kondadega kondades kondadel"
            " konnata konnast konnalt konnaks konnaga kondade konnas konnal kondi"
            " konda"
        ),
    },
    min_len=8,
    caps=True,
    hyphen=True,
)


apply_et = DEFAULT_RULES.apply
