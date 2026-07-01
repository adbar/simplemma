import io
import tarfile

import pytest

from training import download_eval_data
from training.download_eval_data import (
    _safe_extract,
    get_relevant_language_data_folders,
)


def _make_tar(tar_path, member_name, content=b""):
    with tarfile.open(tar_path, "w") as tar:
        info = tarfile.TarInfo(name=member_name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return tar_path


def test_safe_extract_rejects_traversal(tmp_path):
    tar_path = _make_tar(tmp_path / "test.tar", "../escape.txt", b"hello")
    dest = tmp_path / "dest"
    dest.mkdir()

    with (
        tarfile.open(tar_path) as tar,
        pytest.raises(ValueError, match="Illegal tar archive entry"),
    ):
        _safe_extract(tar, dest)


def test_safe_extract_extracts_valid_member(tmp_path):
    tar_path = _make_tar(tmp_path / "ok.tar", "data.txt", b"hello")
    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path) as tar:
        _safe_extract(tar, dest)
    assert (dest / "data.txt").read_bytes() == b"hello"


def test_main_refuses_existing_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(download_eval_data, "DATA_FOLDER", tmp_path)  # already exists
    with pytest.raises(Exception, match="already present"):
        download_eval_data.main()


def test_main_downloads_extracts_and_concatenates(tmp_path, monkeypatch):
    data_folder = tmp_path / "data"
    monkeypatch.setattr(download_eval_data, "DATA_FOLDER", data_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FILE", data_folder / "ud.tgz")
    monkeypatch.setattr(download_eval_data, "CLEAN_DATA_FOLDER", data_folder / "UD")

    content = b"# a German treebank line\nHunde\tHund\n"

    def fake_urlretrieve(url, filename):
        member = "ud-treebanks-v2.12/UD_German-GSD/de_gsd-ud-train.conllu"
        _make_tar(filename, member, content)

    monkeypatch.setattr("urllib.request.urlretrieve", fake_urlretrieve)

    download_eval_data.main()

    concatenated = data_folder / "UD" / "de_gsd.conllu"
    assert concatenated.read_bytes() == content


def test_get_relevant_language_data_folders(tmp_path):
    # supported language
    de_folder = tmp_path / "UD_German-GSD"
    de_folder.mkdir()
    (de_folder / "de_gsd-ud-train.conllu").write_text("")

    # unsupported language code
    xx_folder = tmp_path / "UD_Fake-Test"
    xx_folder.mkdir()
    (xx_folder / "xx_fake-ud-train.conllu").write_text("")

    results = list(get_relevant_language_data_folders(tmp_path))
    assert len(results) == 1
    lang, dataset_name, folder = results[0]
    assert lang == "de"
    assert dataset_name == "de_gsd"
    assert folder == de_folder
