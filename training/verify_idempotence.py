"""Byte-idempotence lint: every shipped dictionary must recompose
byte-identically from its own data (`_compose_dictionary` over the installed
plzma, re-encoded). Zero drift is the invariant since the 2026-08 consistency
pass; ANY difference means a pipeline change silently rewrites shipped data
and must be diagnosed, gated and reshipped deliberately.

Usage: uv run python -m training.verify_idempotence [lang ...]
Exits 1 listing the drifted languages (full run ~15 min).
"""

import argparse
import logging
import sys

from simplemma.strategies.dictionaries import dictionary_factory
from training.dictionary_builder import _compose_dictionary, _encode_dictionary

log = logging.getLogger(__name__)


def drifted_languages(langs: list[str]) -> list[str]:
    """Languages whose recompose is not byte-identical to the shipped plzma."""
    drifted = []
    for lang in langs:
        mydict = _compose_dictionary(lang)
        recomposed = _encode_dictionary(mydict, lang)
        shipped = (dictionary_factory.DATA_FOLDER / f"{lang}.plzma").read_bytes()
        status = "ok" if recomposed == shipped else "DRIFT"
        log.info("%s: %s (%d entries)", lang, status, len(mydict))
        if recomposed != shipped:
            drifted.append(lang)
    return drifted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "langs",
        nargs="*",
        help="language codes to check (default: every shipped language)",
    )
    args = parser.parse_args()

    langs = args.langs or sorted(dictionary_factory.SUPPORTED_LANGUAGES)
    drifted = drifted_languages(langs)
    if drifted:
        sys.exit(f"idempotence DRIFT in {len(drifted)}/{len(langs)}: {drifted}")
    print(f"all {len(langs)} dictionaries recompose byte-identically")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
