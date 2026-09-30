from .generic import SuffixRules

DEFAULT_RULES = SuffixRules(
    {
        "line": "lisesse lisest liselt lisele lisil lisel lises lised lisi lise",
        "lik": "likest",
        "dus": "duses",
        # short stems collide (detailist)
        "iline": ".....ilist iliste",
        "amine": "amist",
        "mine": (
            "mistesse misteta mistest misteni mistena mistelt mistele misteks"
            " mistega misesse mistes mistel miseta misest miseni misena miselt"
            " misele miseks miste mises misel mised mise"
        ),
        "ik": (
            "ikkudele ikkudel ikuta ikuni ikuna ikult ikule ikuks ikuga iketa ikeni"
            " ikena ikelt ikele ikeks ikul ikud ikku ikke iku"
        ),
        "kond": (
            "kondadesse kondadest kondadelt kondadele kondadega kondades kondadel"
            " konnata konnast konnalt konnaks konnaga kondade konnas konnal kondi"
            " konda"
        ),
    },
    min_len=8,
    caps=True,
)


apply_et = DEFAULT_RULES.apply
