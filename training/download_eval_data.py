"""
Fetch the Universal Dependencies treebank archive from LINDAT/CLARIAH-CZ and
lay it out for both consumers: `evaluate_simplemma.py` (one concatenated
train+dev+test file per treebank) and the `training.ud_eval`/`ud_end_to_end`/
`diff_audit` toolkit (per-split files, needed for the tune/dev vs confirm/
test protocol -- concatenation would erase that boundary).

LINDAT migrated to DSpace 7 sometime after the original version of this
script was written: the old `.../xmlui/bitstream/handle/<h>/<file>?sequence=N`
URLs now silently redirect to the JS-rendered item page instead of the file
(no error -- urlretrieve happily saves the HTML shell as if it were the
archive, and tarfile.open() only fails later, confusingly, on extraction).
The DSpace 7 REST API needs three hops: resolve the release HANDLE to an
item UUID, list its ORIGINAL bundle, then match the bitstream by filename.

UD_HANDLE is the only thing that needs bumping to move to a newer release
-- find it at https://universaldependencies.org/, "released through
LINDAT/CLARIAH-CZ" links to a handle of the form 11234/1-XXXX. Bumping it
is a deliberate re-baselining act: rerun `training.ud_eval reliability`
across the evaluation treebanks afterwards, since annotation conventions
can change between releases (see the recorded UD quirks catalog).
"""

import hashlib
import json
import logging
import re
import tarfile
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

UD_VERSION = "2.18"
UD_HANDLE = "11234/1-6149"
API_BASE = "https://lindat.mff.cuni.cz/repository/server/api"

CLEAN_DATA_FOLDER = Path(__file__).parent / "data" / "UD"
DATA_FOLDER = CLEAN_DATA_FOLDER / "_download"  # raw tgz + extracted archive
DATA_FILE = DATA_FOLDER / "ud-treebanks.tgz"
SPLITS_FOLDER = CLEAN_DATA_FOLDER / "splits"
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


def get_dirs(folder: Path) -> list[str]:
    return [d.name for d in folder.iterdir() if d.is_dir()]


# UD's own file-prefix does not always match simplemma's ISO code: Nynorsk
# treebanks are filed under the Norwegian macrolanguage code "no", North
# Sami under "sme". Neither collides with a real SUPPORTED_LANGUAGES entry,
# so without this map they are silently dropped (not misfiled) -- caught by
# comparing output coverage against the expected language list.
_DATASET_LANG_OVERRIDES = {"no_nynorsk": "nn", "sme_giella": "se"}


def get_relevant_language_data_folders(
    data_folder: Path,
) -> Iterable[tuple[str, str, Path]]:
    for lang_folder in get_dirs(data_folder):
        lang_data_folder = data_folder / lang_folder
        conllu_files = list(lang_data_folder.glob("*.conllu"))
        if not conllu_files:
            continue
        matches_files = re.search(r"^(.+)-ud", conllu_files[0].name)
        if matches_files is not None:
            dataset_name = matches_files.groups()[0]
            lang = _DATASET_LANG_OVERRIDES.get(dataset_name, dataset_name.split("_")[0])

            if lang in SUPPORTED_LANGUAGES:
                yield (lang, dataset_name, lang_data_folder)


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    for member in tar.getmembers():
        member_path = (dest / member.name).resolve()
        if not member_path.is_relative_to(dest.resolve()):
            raise ValueError(f"Illegal tar archive entry: {member.name}")
        if hasattr(tarfile, "data_filter"):
            tar.extract(member, dest, filter="data")
        else:
            tar.extract(member, dest)


def main() -> None:
    if DATA_FOLDER.exists() or CLEAN_DATA_FOLDER.exists():
        raise Exception(
            "Data folder seems to be already present. Delete it before creating new data."
        )

    CLEAN_DATA_FOLDER.mkdir()
    DATA_FOLDER.mkdir()
    SPLITS_FOLDER.mkdir()

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
    for lang, dataset_name, dataset_folder in get_relevant_language_data_folders(
        uncompressed_data_folder
    ):
        log.info(f"{lang} - {dataset_folder}")
        # concatenated file for evaluate_simplemma.py, e.g. da_ddt.conllu
        lang_clean_data_file = CLEAN_DATA_FOLDER / f"{dataset_name}.conllu"
        with open(lang_clean_data_file, "wb") as outfile:
            for file in sorted(dataset_folder.glob("*.conllu")):
                with open(file, "rb") as infile:
                    for line in infile:
                        outfile.write(line)
        # per-split files for the tune(dev)/confirm(test) protocol, e.g.
        # da_ddt-ud-train.conllu / -dev.conllu / -test.conllu
        for file in sorted(dataset_folder.glob("*.conllu")):
            (SPLITS_FOLDER / file.name).write_bytes(file.read_bytes())

    VERSION_FILE.write_text(
        f"version={UD_VERSION}\nhandle={UD_HANDLE}\nmd5={expected_md5}\n"
    )
    log.info(f"Done. Wrote provenance to {VERSION_FILE}")


if __name__ == "__main__":
    main()
