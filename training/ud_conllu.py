"""
Shared conventions for reading the UD treebank files fetched by
download_eval_data.py: the dataset-name -> simplemma-code override map and the
one token-iteration convention used by every evaluator/miner (eval_harness,
build_override, eval_gate, and the local eval tooling), so the convention lives
in exactly one place.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from conllu import parse_incr

# UD's file-prefix isn't always simplemma's ISO code (Bokmål="no", Nynorsk="no",
# North Sami="sme") -- without this map they're silently dropped, not misfiled.
# NB: both Norwegian datasets share the "no" prefix, so they must be keyed by
# full dataset name, not the split-on-"_" fallback.
DATASET_LANG_OVERRIDES = {
    "no_bokmaal": "nb",
    "no_nynorsk": "nn",
    "sme_giella": "se",
}


def iter_word_tokens(path: Path) -> Iterator[tuple[str, Any]]:
    """Yield (form, token) for real word tokens, applying the official UD-eval
    convention once: skip MWT/empty-node ids (tuple, not int) and lemma=='_',
    lowercase the sentence-initial (id==1) form. Callers read token['lemma'] /
    token['upos'] as needed."""
    with open(path, encoding="utf-8") as filehandle:
        for tokens in parse_incr(filehandle):
            for token in tokens:
                token_id = token["id"]
                if not isinstance(token_id, int) or token["lemma"] == "_":
                    continue
                form = token["form"].lower() if token_id == 1 else token["form"]
                yield form, token
