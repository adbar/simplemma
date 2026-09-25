"""
Fetch the UD treebank archive from LINDAT/CLARIAH-CZ and copy each supported
language's train/dev/test files to splits/ -- the one on-disk representation
every evaluator (evaluate_simplemma, eval_gate, miners) reads.

Pinned by DSpace bitstream URL + md5. New release: take its handle from
https://universaldependencies.org/#download, then with
API=https://lindat.mff.cuni.cz/repository/server/api
  curl -sI "$API/pid/find?id=hdl:<handle>"        -> Location: .../items/<item>
  curl -s "$API/core/items/<item>/bundles"        -> ORIGINAL bundle uuid
  curl -s "$API/core/bundles/<bundle>/bitstreams" -> content href + checkSum
update the constants, delete training/data/UD/, re-run the evaluation.
"""

import argparse
import hashlib
import logging
import re
import shutil
import tarfile
import urllib.request
from collections.abc import Iterable
from pathlib import Path

from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES
from training.ud_conllu import UD_SPLITS, dataset_to_lang

log = logging.getLogger(__name__)

UD_VERSION = "2.18"
UD_HANDLE = "11234/1-6149"
BITSTREAM_URL = (
    "https://lindat.mff.cuni.cz/repository/server/api/core/bitstreams/"
    "d91b1ffc-fc31-41a0-bd8f-3b876864a1d5/content"
)
BITSTREAM_MD5 = "e9bfd544a48eac63ea3bb41e80c78813"

CLEAN_DATA_FOLDER = UD_SPLITS.parent
DATA_FOLDER = CLEAN_DATA_FOLDER / "_download"  # raw tgz + extracted archive
DATA_FILE = DATA_FOLDER / "ud-treebanks.tgz"
VERSION_FILE = CLEAN_DATA_FOLDER / "UD_VERSION"


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

    log.info(f"Downloading UD {UD_VERSION} (handle {UD_HANDLE})...")
    urllib.request.urlretrieve(BITSTREAM_URL, DATA_FILE)
    actual_md5 = _md5(DATA_FILE)
    if actual_md5 != BITSTREAM_MD5:
        raise RuntimeError(
            f"checksum mismatch for UD {UD_VERSION}: expected {BITSTREAM_MD5}, "
            f"got {actual_md5}"
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
        f"version={UD_VERSION}\nhandle={UD_HANDLE}\nmd5={BITSTREAM_MD5}\n"
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
