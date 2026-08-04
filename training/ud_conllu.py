"""Shared conventions for reading the UD treebank files fetched by
download_eval_data.py: the dataset-name -> simplemma-code override map and
the one token-iteration convention used by every evaluator/miner."""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from conllu import parse_incr

from simplemma.utils import canonicalize_token

# UD's file-prefix isn't always simplemma's ISO code -- both Norwegian sets
# share "no", North Sami is "sme" -- so key by full dataset name here.
DATASET_LANG_OVERRIDES = {
    "no_bokmaal": "nb",
    "no_nynorsk": "nn",
    "sme_giella": "se",
    "hr_set": "hbs",
    "sr_set": "hbs",
}


def dataset_to_lang(dataset_name: str) -> str:
    """Map a UD dataset name (e.g. ``ro_rrt``, ``no_bokmaal``) to simplemma's
    language code: an explicit override, else the prefix before the first ``_``."""
    return DATASET_LANG_OVERRIDES.get(dataset_name, dataset_name.split("_", 1)[0])


# Which sub-token of a fused MWT span carries the "real" lemma a user cares
# about (he/ar proclitics+article fuse onto a NOUN/VERB/etc.; the proclitic
# itself is a closed-class function word, not what a lemmatizer is judged on).
CONTENT_POS = frozenset({"NOUN", "VERB", "ADJ", "PROPN", "ADV", "NUM"})


def _strip_mwt_artifact(value: str) -> str:
    """Strip the leading/trailing underscore some treebanks (he_htb) use to
    mark the elided side of an MWT sub-token split (e.g. 'יכולת_', '_של_').
    A value stripping to nothing (the null '_', et_ewt's underscore-run
    PUNCT token) is returned unchanged -- never emit an empty form/lemma."""
    return value.strip("_") or value


# fi/et/hu gold lemmas mark compound boundaries (yli#opisto, sisse_tulek,
# el+mond); stripping them fixed 36.8% of fi errors, 42.3% of et. Per-language
# because '_' is a real convention in e.g. nl Alpino lemmas.
_GOLD_COMPOUND_SEPARATORS = {"fi": "#", "et": "_", "hu": "+"}


def canon_lemma(lemma: str, form: str, lang: str) -> str:
    """The gold-lemma transform every reader shares: strip the MWT artifact
    and the language's compound-boundary markers, then canonicalize for
    `lang` (a no-op outside _CANON_TABLES), so gold is compared/mined in the
    shipped dict's own key space.

    A marker also present in `form` belongs to the token ('#luonto', '16+3'),
    not to the annotation, so the strip is skipped there; a real compound
    marker never survives into the form (yli#opisto -> yliopisto). `form` may
    arrive already MWT-stripped -- the strip is idempotent."""
    lemma = _strip_mwt_artifact(lemma)
    separator = _GOLD_COMPOUND_SEPARATORS.get(lang)
    if separator and separator in lemma and lemma != _strip_mwt_artifact(form):
        # `or lemma`: an all-marker lemma must not strip to nothing. Unreachable
        # in UD 2.18 (every such lemma equals its form, so the gate above skips
        # it) but that is a property of the data, not of the code -- without it
        # a UD bump could turn gold into "" and score every prediction wrong.
        lemma = lemma.replace(separator, "") or lemma
    return canonicalize_token(lemma, lang)


def iter_word_tokens_in_sentences(
    sentences: Iterable[Any], lang: str
) -> Iterator[tuple[str, Any]]:
    """Yield (form, token) for real word tokens, applying the official UD-eval
    convention: skip MWT/empty-node ids (tuple, not int) and lemma=='_',
    lowercase the sentence-initial (id==1) form.

    Mutates token["form"]/token["lemma"] in place -- MWT-artifact stripped
    and the LEMMA canonicalized via `canon_lemma`. Centralizing it here means
    every reader (eval harnesses AND build_override) inherits the same gold
    key space with no per-caller step to forget."""
    for tokens in sentences:
        for token in tokens:
            token_id = token["id"]
            if not isinstance(token_id, int) or token["lemma"] == "_":
                continue
            token["form"] = _strip_mwt_artifact(token["form"])
            token["lemma"] = canon_lemma(token["lemma"], token["form"], lang)
            form = token["form"].lower() if token_id == 1 else token["form"]
            yield form, token


def iter_word_tokens(path: Path, lang: str) -> Iterator[tuple[str, Any]]:
    """iter_word_tokens_in_sentences over the conllu file at `path`."""
    with open(path, encoding="utf-8") as filehandle:
        yield from iter_word_tokens_in_sentences(parse_incr(filehandle), lang)
