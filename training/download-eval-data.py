import logging
import re
import tarfile
from glob import glob
from os import mkdir, path, scandir
from typing import Iterable, List, Tuple

import requests

from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
DATA_URL = "https://lindat.mff.cuni.cz/repository/xmlui/bitstream/handle/11234/1-5150/ud-treebanks-v2.12.tgz?sequence=1&isAllowed=y"
DATA_FOLDER = path.join(path.dirname(__file__), "data")
DATA_FILE = path.join(DATA_FOLDER, "ud-treeebanks.tgz")
CLEAN_DATA_FOLDER = path.join(DATA_FOLDER, "UD")


def get_dirs(file_name: str) -> List[str]:
    return [dir.name for dir in scandir(file_name) if dir.is_dir()]


def get_files(file_name: str) -> List[str]:
    return [dir.name for dir in scandir(file_name) if dir.is_file()]


def get_relevant_language_data_folders(data_folder) -> Iterable[Tuple[str, str, str]]:
    for lang_folder in get_dirs(data_folder):
        lang_data_folder = path.join(uncompressed_data_folder, lang_folder)
        conllu_file = glob(path.join(lang_data_folder, "*.conllu"))[0]
        matches_files = re.search("^.*/(.*)-ud.*$", conllu_file)
        if matches_files is not None:
            dataset_name = matches_files.groups()[0]
            lang = dataset_name.split("_")[0]

            if lang in SUPPORTED_LANGUAGES:
                yield (lang, dataset_name, lang_data_folder)


if path.exists(DATA_FOLDER) or path.exists(CLEAN_DATA_FOLDER):
    raise Exception(
        "Data folder seems to be already present. Delete it before creating new data."
    )

mkdir(DATA_FOLDER)
mkdir(CLEAN_DATA_FOLDER)

log.info("Downloading evaluation data...")
response = requests.get(DATA_URL)
open(DATA_FILE, "wb").write(response.content)

log.info("Uncompressing evaluation data...")
with tarfile.open(DATA_FILE) as tar:
    tar.extractall(DATA_FOLDER)
uncompressed_data_folder = path.join(
    DATA_FOLDER, glob(f"{DATA_FOLDER}/ud-treebanks-*")[0]
)

log.info("Filtering files...")
for lang, dataset_name, dataset__folder in get_relevant_language_data_folders(
    uncompressed_data_folder
):
    log.info(lang + " - " + dataset__folder)
    # Concatenate the train, dev and test data into a single file (e.g. ``cat de_gsd*.conllu > de-gsd-all.conllu``)
    lang_clean_data_file = path.join(CLEAN_DATA_FOLDER, f"{dataset_name}.conllu")
    log.debug(f"Procressing data for {dataset_name}")
    with open(lang_clean_data_file, "w") as outfile:
        for file in glob(path.join(dataset__folder, "*.conllu")):
            with open(file) as infile:
                for line in infile:
                    outfile.write(line)
