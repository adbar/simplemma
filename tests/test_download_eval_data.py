import io
import tarfile

import pytest

from training import download_eval_data
from training.download_eval_data import (
    _md5,
    _safe_extract,
    get_relevant_language_data_folders,
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


def test_main_downloads_extracts_and_writes_splits(tmp_path, monkeypatch):
    clean_folder = tmp_path / "UD"
    data_folder = clean_folder / "_download"
    splits_folder = clean_folder / "splits"
    version_file = clean_folder / "UD_VERSION"
    monkeypatch.setattr(download_eval_data, "CLEAN_DATA_FOLDER", clean_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FOLDER", data_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FILE", data_folder / "ud.tgz")
    monkeypatch.setattr(download_eval_data, "UD_SPLITS", splits_folder)
    monkeypatch.setattr(download_eval_data, "VERSION_FILE", version_file)

    train_content = b"# a German treebank line\nHunde\tHund\n"
    dev_content = b"# a German treebank line\nKatzen\tKatze\n"

    monkeypatch.setattr(download_eval_data, "resolve_item_uuid", lambda handle: "uuid")
    monkeypatch.setattr(
        download_eval_data,
        "find_treebanks_bitstream",
        lambda item_uuid, filename: (
            "https://example.invalid/archive.tgz",
            "sentinel-md5",
        ),
    )
    monkeypatch.setattr(download_eval_data, "_md5", lambda path: "sentinel-md5")

    def fake_urlretrieve(url, filename):
        version = download_eval_data.UD_VERSION
        base = f"ud-treebanks-v{version}/UD_German-GSD"
        _make_tar(
            filename,
            {
                f"{base}/de_gsd-ud-train.conllu": train_content,
                f"{base}/de_gsd-ud-dev.conllu": dev_content,
            },
        )

    monkeypatch.setattr("urllib.request.urlretrieve", fake_urlretrieve)

    download_eval_data.main()

    assert (splits_folder / "de_gsd-ud-train.conllu").read_bytes() == train_content
    assert (splits_folder / "de_gsd-ud-dev.conllu").read_bytes() == dev_content
    assert version_file.exists()
    assert "sentinel-md5" in version_file.read_text()


def test_main_raises_on_checksum_mismatch(tmp_path, monkeypatch):
    clean_folder = tmp_path / "UD"
    data_folder = clean_folder / "_download"
    monkeypatch.setattr(download_eval_data, "CLEAN_DATA_FOLDER", clean_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FOLDER", data_folder)
    monkeypatch.setattr(download_eval_data, "DATA_FILE", data_folder / "ud.tgz")
    monkeypatch.setattr(download_eval_data, "UD_SPLITS", clean_folder / "splits")
    monkeypatch.setattr(download_eval_data, "VERSION_FILE", clean_folder / "UD_VERSION")

    monkeypatch.setattr(download_eval_data, "resolve_item_uuid", lambda handle: "uuid")
    monkeypatch.setattr(
        download_eval_data,
        "find_treebanks_bitstream",
        lambda item_uuid, filename: (
            "https://example.invalid/archive.tgz",
            "expected-md5",
        ),
    )
    monkeypatch.setattr(
        "urllib.request.urlretrieve",
        lambda url, filename: filename.write_bytes(b"not the real archive"),
    )

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        download_eval_data.main()


def test_get_relevant_language_data_folders(tmp_path):
    # supported language
    de_folder = tmp_path / "UD_German-GSD"
    de_folder.mkdir()
    (de_folder / "de_gsd-ud-train.conllu").write_text("")

    # unsupported language code
    xx_folder = tmp_path / "UD_Fake-Test"
    xx_folder.mkdir()
    (xx_folder / "xx_fake-ud-train.conllu").write_text("")

    # dataset name doesn't map to the ISO code directly -> override table
    nn_folder = tmp_path / "UD_Norwegian-Nynorsk"
    nn_folder.mkdir()
    (nn_folder / "no_nynorsk-ud-train.conllu").write_text("")

    # no conllu files at all -> skipped, not a crash
    empty_folder = tmp_path / "UD_Empty-Test"
    empty_folder.mkdir()

    results = dict(get_relevant_language_data_folders(tmp_path))

    assert results == {"de": de_folder, "nn": nn_folder}
