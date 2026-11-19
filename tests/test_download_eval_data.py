import io
import tarfile

import pytest

from training import download_eval_data
from training.download_eval_data import (
    _md5,
    _safe_extract,
    get_relevant_language_data_folders,
    treebank_license,
)


def _make_tar(tar_path, members):
    "members: dict[name, content] or a single (name, content) pair."
    if isinstance(members, tuple):
        members = dict([members])
    with tarfile.open(tar_path, "w") as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return tar_path


def test_safe_extract_rejects_traversal(tmp_path):
    tar_path = _make_tar(tmp_path / "test.tar", ("../escape.txt", b"hello"))
    dest = tmp_path / "dest"
    dest.mkdir()

    with (
        tarfile.open(tar_path) as tar,
        pytest.raises(ValueError, match="Illegal tar archive entry"),
    ):
        _safe_extract(tar, dest)


def test_safe_extract_extracts_valid_member(tmp_path):
    tar_path = _make_tar(tmp_path / "ok.tar", ("data.txt", b"hello"))
    dest = tmp_path / "dest"
    dest.mkdir()

    with tarfile.open(tar_path) as tar:
        _safe_extract(tar, dest)
    assert (dest / "data.txt").read_bytes() == b"hello"


def test_md5(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"hello")
    assert _md5(path) == "5d41402abc4b2a76b9719d911017c592"


def test_main_refuses_existing_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(download_eval_data, "CLEAN_DATA_FOLDER", tmp_path)
    with pytest.raises(Exception, match="already present"):
        download_eval_data.main()


TRAIN = b"# a German treebank line\nHunde\tHund\n"
DEV = b"# a German treebank line\nKatzen\tKatze\n"


def _fake_release(tmp_path, monkeypatch, readme: bytes):
    """Patch main() to 'download' a one-treebank release, return the UD folder."""
    clean_folder = tmp_path / "UD"
    data_folder = clean_folder / "_download"
    monkeypatch.setattr(download_eval_data, "CLEAN_DATA_FOLDER", clean_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FOLDER", data_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FILE", data_folder / "ud.tgz")
    monkeypatch.setattr(download_eval_data, "UD_SPLITS", clean_folder / "splits")
    monkeypatch.setattr(download_eval_data, "VERSION_FILE", clean_folder / "UD_VERSION")
    monkeypatch.setattr(download_eval_data, "UD_LICENSES", clean_folder / "lic.tsv")
    monkeypatch.setattr(download_eval_data, "BITSTREAM_MD5", "sentinel-md5")
    monkeypatch.setattr(download_eval_data, "_md5", lambda path: "sentinel-md5")

    def fake_urlretrieve(url, filename):
        base = f"ud-treebanks-v{download_eval_data.UD_VERSION}/UD_German-GSD"
        _make_tar(
            filename,
            {
                f"{base}/de_gsd-ud-train.conllu": TRAIN,
                f"{base}/de_gsd-ud-dev.conllu": DEV,
                f"{base}/README.md": readme,
            },
        )

    monkeypatch.setattr("urllib.request.urlretrieve", fake_urlretrieve)
    return clean_folder


def test_main_downloads_extracts_and_writes_splits(tmp_path, monkeypatch):
    readme = b"# Summary\n\nLicense: CC BY-SA 4.0\n"
    clean_folder = _fake_release(tmp_path, monkeypatch, readme)

    download_eval_data.main()

    assert (clean_folder / "splits" / "de_gsd-ud-train.conllu").read_bytes() == TRAIN
    assert (clean_folder / "splits" / "de_gsd-ud-dev.conllu").read_bytes() == DEV
    assert "sentinel-md5" in (clean_folder / "UD_VERSION").read_text()
    assert (clean_folder / "lic.tsv").read_text() == "de_gsd\tCC BY-SA 4.0\n"


def test_main_raises_without_any_license(tmp_path, monkeypatch):
    clean_folder = _fake_release(tmp_path, monkeypatch, b"# Summary\n")
    with pytest.raises(RuntimeError, match="no 'License:' line"):
        download_eval_data.main()
    assert not (clean_folder / "lic.tsv").exists()


def test_main_raises_on_checksum_mismatch(tmp_path, monkeypatch):
    clean_folder = tmp_path / "UD"
    data_folder = clean_folder / "_download"
    monkeypatch.setattr(download_eval_data, "CLEAN_DATA_FOLDER", clean_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FOLDER", data_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FILE", data_folder / "ud.tgz")
    monkeypatch.setattr(download_eval_data, "UD_SPLITS", clean_folder / "splits")
    monkeypatch.setattr(download_eval_data, "VERSION_FILE", clean_folder / "UD_VERSION")

    monkeypatch.setattr(download_eval_data, "BITSTREAM_MD5", "expected-md5")
    monkeypatch.setattr(
        "urllib.request.urlretrieve",
        lambda url, filename: filename.write_bytes(b"not the real archive"),
    )

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        download_eval_data.main()


def test_get_relevant_language_data_folders(tmp_path):
    de_folder = tmp_path / "UD_German-GSD"
    de_folder.mkdir()
    (de_folder / "de_gsd-ud-train.conllu").write_text("")

    xx_folder = tmp_path / "UD_Fake-Test"
    xx_folder.mkdir()
    (xx_folder / "xx_fake-ud-train.conllu").write_text("")

    # no_nynorsk maps to nn through the override table
    nn_folder = tmp_path / "UD_Norwegian-Nynorsk"
    nn_folder.mkdir()
    (nn_folder / "no_nynorsk-ud-train.conllu").write_text("")

    empty_folder = tmp_path / "UD_Empty-Test"
    empty_folder.mkdir()

    results = dict(get_relevant_language_data_folders(tmp_path))

    assert results == {"de": de_folder, "nn": nn_folder}


def test_treebank_license(tmp_path):
    assert treebank_license(tmp_path) is None
    (tmp_path / "README.txt").write_text("Summary\n\nlicense:  CC BY 4.0  \n")
    assert treebank_license(tmp_path) == "CC BY 4.0"
    (tmp_path / "README.txt").write_text("License:\n# Changelog\nLicense: CC BY 4.0\n")
    assert treebank_license(tmp_path) == "CC BY 4.0"
