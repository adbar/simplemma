import re

from .generic import apply_rules

DEFAULT_RULES = {
    re.compile(r"(?:ościach|ościami|ościom)$"): "ość",  # removed: "ością", "ości"
    re.compile(
        r"(?:owałem|owałam|owaliśmy|owałeś|owałaś|owaliście|owałbym|owałabym|owalibyśmy|owałbyś|owałabyś|owalibyście|owałby|owałaby|owałoby|owaliby|owałyby|owanie)$"
    ): "ować",
    # re.compile(r"(?:skie|skiego|skiemu|skiej|skich|skim|skimi|ską|scy)$"): "ski",
    # past tense + conditional (aliście dropped: collides with -alista locatives)
    re.compile(r"(?:aliśmy|alibyście|alibyśmy)$"): "ać",
    re.compile(
        r"(?:ił|iła|iło|iły|iłem|iłam|iłeś|iłaś|iłyśmy|iłyście|iliśmy|iliście|iłybyście|ilibyście|ilibyśmy|iłybyśmy)$"
    ): "ić",
    re.compile(
        r"(?:ył|yła|yło|yły|yłem|yłam|yłeś|yłaś|yłyśmy|yłyście|yliśmy|yliście|yłybyście|ylibyście|ylibyśmy|yłybyśmy)$"
    ): "yć",
}


def apply_pl(token: str) -> str | None:
    "Apply pre-defined rules for Polish."
    return apply_rules(token, DEFAULT_RULES, min_len=8, caps=True, hyphen=True)
