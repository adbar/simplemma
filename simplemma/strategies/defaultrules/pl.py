import re
from typing import Optional

from .generic import apply_rules

DEFAULT_RULES = {
    re.compile(r"(?:ościach|ościami|ościom)$"): "ość",  # removed: "ością", "ości"
    re.compile(
        r"(?:owałem|owałam|owaliśmy|owałeś|owałaś|owaliście|owałbym|owałabym|owalibyśmy|owałbyś|owałabyś|owalibyście|owałby|owałaby|owałoby|owaliby|owałyby|owanie)$"
    ): "ować",
    re.compile(r"(?:ościach|ościami|ościom)$"): "ość",
    # re.compile(r"(?:skie|skiego|skiemu|skiej|skich|skim|skimi|ską|scy)$"): "ski",
    re.compile(r"(?:alibyście|alibyśmy)$"): "ać",
    re.compile(r"(?:iłybyście|ilibyście|ilibyśmy|iłybyśmy)$"): "ić",
    re.compile(r"(?:yłybyście|ylibyście|ylibyśmy|yłybyśmy)$"): "yć",
}


def apply_pl(token: str) -> Optional[str]:
    "Apply pre-defined rules for Polish."
    if len(token) < 10 or token[0].isupper():
        return None

    return apply_rules(token, DEFAULT_RULES)
