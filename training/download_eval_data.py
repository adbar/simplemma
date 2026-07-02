import logging
import re
import tarfile
import urllib.request
from collections.abc import Iterable
from pathlib import Path

from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
DATA_URL = "https://lindat.mff.cuni.cz/repository/xmlui/bitstream/handle/11234/1-5150/ud-treebanks-v2.12.tgz?sequence=1&isAllowed=y"
DATA_FOLDER = Path(__file__).parent / "data"
DATA_FILE = DATA_FOLDER / "ud-treeebanks.tgz"
CLEAN_DATA_FOLDER = DATA_FOLDER / "UD"


def get_dirs(folder: Path) -> list[str]:
    return [d.name for d in folder.iterdir() if d.is_dir()]


def get_relevant_language_data_folders(
    data_folder: Path,
) -> Iterable[tuple[str, str, Path]]:
    for lang_folder in get_dirs(data_folder):
        lang_data_folder = data_folder / lang_folder
        conllu_file = next(lang_data_folder.glob("*.conllu"))
        matches_files = re.search(r"^(.+)-ud", conllu_file.name)
        if matches_files is not None:
            dataset_name = matches_files.groups()[0]
            lang = dataset_name.split("_")[0]

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

    DATA_FOLDER.mkdir()
    CLEAN_DATA_FOLDER.mkdir()

    log.info("Downloading evaluation data...")
    urllib.request.urlretrieve(DATA_URL, DATA_FILE)

    log.info("Uncompressing evaluation data...")
    with tarfile.open(DATA_FILE) as tar:
        _safe_extract(tar, DATA_FOLDER)
    uncompressed_data_folder = next(DATA_FOLDER.glob("ud-treebanks-*"))

    log.info("Filtering files...")
    for lang, dataset_name, dataset__folder in get_relevant_language_data_folders(
        uncompressed_data_folder
    ):
        log.info(f"{lang} - {dataset__folder}")
        # Concatenate the train, dev and test data into a single file
        # (e.g. de_gsd-ud-{train,dev,test}.conllu -> de_gsd.conllu)
        lang_clean_data_file = CLEAN_DATA_FOLDER / f"{dataset_name}.conllu"
        log.debug(f"Procressing data for {dataset_name}")
        with open(lang_clean_data_file, "wb") as outfile:
            for file in sorted(dataset__folder.glob("*.conllu")):
                with open(file, "rb") as infile:
                    for line in infile:
                        outfile.write(line)


if __name__ == "__main__":
    main()
