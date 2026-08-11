"""
Fetch the UD treebank archive from LINDAT/CLARIAH-CZ and copy each supported
language's train/dev/test files to splits/ -- the one on-disk representation
every evaluator (evaluate_simplemma, eval_gate, miners) reads.

LINDAT runs DSpace 7: old bitstream URLs silently redirect to an HTML page,
so the REST API is used (handle -> item UUID -> ORIGINAL bundle -> bitstream).
To move to a newer release, bump UD_HANDLE and re-run the evaluation
(annotation conventions change between releases).
"""

import argparse
import hashlib
import json
import logging
import re
import shutil
import tarfile
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES
from training.ud_conllu import UD_SPLITS, dataset_to_lang

log = logging.getLogger(__name__)

UD_VERSION = "2.18"
UD_HANDLE = "11234/1-6149"
API_BASE = "https://lindat.mff.cuni.cz/repository/server/api"

CLEAN_DATA_FOLDER = UD_SPLITS.parent
DATA_FOLDER = CLEAN_DATA_FOLDER / "_download"  # raw tgz + extracted archive
DATA_FILE = DATA_FOLDER / "ud-treebanks.tgz"
VERSION_FILE = CLEAN_DATA_FOLDER / "UD_VERSION"


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url) as resp:
        result: dict[str, Any] = json.load(resp)
        return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def resolve_item_uuid(handle: str) -> str:
    "PID lookup: a handle resolves to a 302 whose Location has the item UUID."
    url = f"{API_BASE}/pid/find?id=hdl:{handle}"
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        opener.open(url)
        location = ""
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location") or ""
    match = re.search(r"/items/([0-9a-f-]{36})", location)
    if not match:
        raise RuntimeError(f"could not resolve handle {handle}: Location={location!r}")
    return match.group(1)


def find_treebanks_bitstream(item_uuid: str, filename: str) -> tuple[str, str]:
    "Returns (content_url, md5) for `filename` in the item's ORIGINAL bundle."
    bundles = _get_json(f"{API_BASE}/core/items/{item_uuid}/bundles")
    original = next(
        b for b in bundles["_embedded"]["bundles"] if b["name"] == "ORIGINAL"
    )
    bitstreams = _get_json(f"{API_BASE}/core/bundles/{original['uuid']}/bitstreams")
    bitstream = next(
        b for b in bitstreams["_embedded"]["bitstreams"] if b["name"] == filename
    )
    content_url = bitstream["_links"]["content"]["href"]
    md5 = bitstream["checkSum"]["value"]
    return content_url, md5


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_relevant_language_data_folders(
    data_folder: Path,
) -> Iterable[tuple[str, Path]]:
    for lang_data_folder in data_folder.iterdir():
        if not lang_data_folder.is_dir():
            continue
        conllu_files = list(lang_data_folder.glob("*.conllu"))
        if not conllu_files:
            continue
        matches_files = re.search(r"^(.+)-ud", conllu_files[0].name)
        if matches_files is not None:
            lang = dataset_to_lang(matches_files.groups()[0])
            if lang in SUPPORTED_LANGUAGES:
                yield (lang, lang_data_folder)


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    for member in tar.getmembers():
        member_path = (dest / member.name).resolve()
        if not member_path.is_relative_to(dest.resolve()):
            raise ValueError(f"Illegal tar archive entry: {member.name}")
        if hasattr(tarfile, "data_filter"):
            tar.extract(member, dest, filter="data")
        else:
            tar.extract(member, dest)


def main(keep_download: bool = False) -> None:
    if DATA_FOLDER.exists() or CLEAN_DATA_FOLDER.exists():
        raise Exception(
            "Data folder seems to be already present. Delete it before creating new data."
        )

    CLEAN_DATA_FOLDER.mkdir()
    DATA_FOLDER.mkdir()
    UD_SPLITS.mkdir()

    filename = f"ud-treebanks-v{UD_VERSION}.tgz"
    log.info(f"Resolving UD {UD_VERSION} (handle {UD_HANDLE})...")
    item_uuid = resolve_item_uuid(UD_HANDLE)
    content_url, expected_md5 = find_treebanks_bitstream(item_uuid, filename)

    log.info(f"Downloading {filename}...")
    urllib.request.urlretrieve(content_url, DATA_FILE)
    actual_md5 = _md5(DATA_FILE)
    if actual_md5 != expected_md5:
        raise RuntimeError(
            f"checksum mismatch for {filename}: expected {expected_md5}, got {actual_md5}"
        )

    log.info("Uncompressing evaluation data...")
    with tarfile.open(DATA_FILE) as tar:
        _safe_extract(tar, DATA_FOLDER)
    uncompressed_data_folder = next(DATA_FOLDER.glob("ud-treebanks-*"))

    log.info("Filtering files...")
    for lang, dataset_folder in get_relevant_language_data_folders(
        uncompressed_data_folder
    ):
        log.info(f"{lang} - {dataset_folder}")
        for file in sorted(dataset_folder.glob("*.conllu")):
            (UD_SPLITS / file.name).write_bytes(file.read_bytes())

    VERSION_FILE.write_text(
        f"version={UD_VERSION}\nhandle={UD_HANDLE}\nmd5={expected_md5}\n"
    )

    # nothing downstream reads the raw download (several GB); kept only on
    # request -- useful once for hand-recovering a missing treebank
    if not keep_download:
        log.info("Removing raw download folder...")
        shutil.rmtree(DATA_FOLDER)

    log.info(f"Done. Wrote provenance to {VERSION_FILE}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-download",
        action="store_true",
        help="keep the raw tgz + extracted archive under data/UD/_download/ "
        "(several GB; nothing downstream reads it)",
    )
    main(keep_download=parser.parse_args().keep_download)
