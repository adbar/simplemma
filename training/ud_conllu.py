"""Shared conventions for reading the UD treebank files."""

import logging
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from conllu import parse_incr

from simplemma.utils import canonicalize_token, normalize_token

log = logging.getLogger(__name__)

UD_SPLITS = Path(__file__).parent / "data" / "UD" / "splits"
# Dataset name to the license line of its README, written at download.
UD_LICENSES = UD_SPLITS.parent / "licenses.tsv"

DATASET_LANG_OVERRIDES = {
    "no_bokmaal": "nb",
    "no_nynorsk": "nn",
    "sme_giella": "se",
    "hr_set": "hbs",
    "sr_set": "hbs",
}


def dataset_to_lang(dataset_name: str) -> str:
    """Map a UD dataset name (e.g. ``ro_rrt``) to simplemma's language code."""
    return DATASET_LANG_OVERRIDES.get(dataset_name, dataset_name.split("_", 1)[0])


def dataset_name(path: Path) -> str:
    """Dataset name of a ``{dataset}-ud-{split}.conllu`` file (``ro_rrt``)."""
    return path.name.split("-ud-", 1)[0]


def discover_treebanks(
    lang: str, split: str, ud_splits: Path | None = None
) -> list[Path]:
    """Every *-ud-<split>.conllu file whose dataset belongs to `lang`."""
    suffix = f"-ud-{split}.conllu"
    return sorted(
        path
        for path in (ud_splits or UD_SPLITS).glob(f"*{suffix}")
        if dataset_to_lang(dataset_name(path)) == lang
    )


FREE_LICENSE = re.compile(r"CC BY(-SA)? \d\.\d|CC0( 1\.0)?|Public Domain")
# Digital humanities languages, where non-commercial data is accepted.
NC_LICENSE = re.compile(r"CC BY-NC-SA \d\.\d")
NC_LANGS = frozenset({"grc", "la"})


def read_licenses(path: Path | None = None) -> dict[str, str]:
    """Dataset name to license. Exits if the file is missing."""
    path = path or UD_LICENSES
    if not path.exists():
        sys.exit(
            f"no {path}, move training/data/UD/ aside "
            "and re-run training.download_eval_data"
        )
    lines = path.read_text(encoding="utf-8").splitlines()
    return dict(line.split("\t", 1) for line in lines if line)


def allowed_license(lic: str, lang: str) -> bool:
    """CC BY, CC BY-SA, CC0 or public domain, plus CC BY-NC-SA for NC_LANGS."""
    return bool(
        FREE_LICENSE.fullmatch(lic) or (lang in NC_LANGS and NC_LICENSE.fullmatch(lic))
    )


def licensed_treebanks(paths: Iterable[Path], lang: str) -> list[Path]:
    """Train paths under an allowed license. Warns on each other, exits if none."""
    licenses = read_licenses()
    kept = []
    for path in paths:
        name = dataset_name(path)
        lic = licenses.get(name, "")
        if allowed_license(lic, lang):
            kept.append(path)
        else:
            log.warning(f"{lang}: skipping {name} ({lic or 'no license'})")
    if not kept:
        sys.exit(f"no train split under an allowed license for {lang!r}")
    return kept


def _strip_mwt_artifact(value: str) -> str:
    """Strip edge underscores marking MWT parts, unless nothing would remain."""
    return value.strip("_") or value


# Gold compound-boundary markers (yli#opisto), per language as '_' is real elsewhere.
_GOLD_COMPOUND_SEPARATORS = {"fi": "#", "et": "_", "hu": "+"}


def canon_lemma(lemma: str, form: str, lang: str) -> str:
    """Gold lemma cleaned of markers and folded into the shipped dict's key space."""
    lemma = _strip_mwt_artifact(lemma)
    separator = _GOLD_COMPOUND_SEPARATORS.get(lang)
    if separator and separator in lemma:
        lemma = _strip_compound_markers(lemma, _strip_mwt_artifact(form), separator)
    return canonicalize_token(normalize_token(lemma), lang)


def _strip_compound_markers(lemma: str, form: str, separator: str) -> str:
    """Strip compound markers from `lemma` unless `form` shows them as content."""
    core = lemma.strip(separator)
    if not core or separator in form.strip(separator):
        return lemma
    head = lemma[: len(lemma) - len(lemma.lstrip(separator))]
    tail = lemma[len(lemma.rstrip(separator)) :]
    if not form.startswith(separator):
        head = ""
    if not form.endswith(separator):
        tail = ""
    return head + core.replace(separator, "") + tail


def iter_word_tokens_in_sentences(
    sentences: Iterable[Any], lang: str
) -> Iterator[tuple[str, Any]]:
    """Yield (form, token) for word tokens, lowercasing sentence-initial forms.

    Normalizes token["form"] and token["lemma"] in place."""
    for tokens in sentences:
        for token in tokens:
            token_id = token["id"]
            # ar_nyuad ships "_" forms with real lemmas.
            if not isinstance(token_id, int) or "_" in (token["form"], token["lemma"]):
                continue
            token["form"] = normalize_token(_strip_mwt_artifact(token["form"]))
            token["lemma"] = canon_lemma(token["lemma"], token["form"], lang)
            form = token["form"].lower() if token_id == 1 else token["form"]
            yield form, token


def iter_word_tokens(path: Path, lang: str) -> Iterator[tuple[str, Any]]:
    """iter_word_tokens_in_sentences over the conllu file at `path`."""
    with open(path, encoding="utf-8") as filehandle:
        yield from iter_word_tokens_in_sentences(parse_incr(filehandle), lang)
