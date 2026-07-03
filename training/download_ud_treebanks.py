"""
Idempotent downloader for the UD treebanks used by the affix-decomposition
research (training/data/affix_eval/). Files land in
training/data/affix_eval/ud/ (git-ignored); existing files are kept, so the
data survives across sessions and is only fetched once per machine.

Pinned to the UD r2.12 release tag for reproducibility. After downloading,
verifies against ud/SHA256SUMS when that manifest is present (it is written
on first download), so silent upstream or on-disk changes are caught.

Usage: uv run python training/download_ud_treebanks.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

UD_TAG = "r2.12"
# repo -> (file prefix, tag override). Prefix follows the treebank's own UD
# code, which does not always match simplemma's lang code (North Sami is
# "sme" upstream, Norwegian Nynorsk is filed under "no"). Tag override is
# used for treebanks added to UD after r2.12 (Georgian-GLC: r2.13,
# Luxembourgish-LuxBank: r2.14) -- earliest tag each has, per their GitHub
# tag lists.
TREEBANKS: dict[str, tuple[str, str | None]] = {
    # affix-decomposition round
    "UD_Bulgarian-BTB": ("bg_btb", None),
    "UD_Catalan-AnCora": ("ca_ancora", None),
    "UD_Danish-DDT": ("da_ddt", None),
    "UD_Icelandic-Modern": ("is_modern", None),
    "UD_Lithuanian-ALKSNIS": ("lt_alksnis", None),
    "UD_Polish-PDB": ("pl_pdb", None),
    "UD_Portuguese-Bosque": ("pt_bosque", None),
    "UD_Romanian-RRT": ("ro_rrt", None),
    "UD_Russian-GSD": ("ru_gsd", None),
    "UD_Spanish-GSD": ("es_gsd", None),
    # rules-overhaul validation round
    "UD_Latvian-LVTB": ("lv_lvtb", None),
    "UD_Finnish-TDT": ("fi_tdt", None),
    "UD_Estonian-EDT": ("et_edt", None),
    "UD_English-EWT": ("en_ewt", None),
    "UD_Dutch-Alpino": ("nl_alpino", None),
    "UD_Ukrainian-IU": ("uk_iu", None),
    "UD_Czech-CAC": ("cs_cac", None),
    "UD_Latin-ITTB": ("la_ittb", None),
    "UD_Swedish-Talbanken": ("sv_talbanken", None),
    "UD_North_Sami-Giella": ("sme_giella", None),  # no dev split upstream
    "UD_Norwegian-Nynorsk": ("no_nynorsk", None),
    "UD_Luxembourgish-LuxBank": ("lb_luxbank", "r2.14"),
    "UD_Georgian-GLC": ("ka_glc", "r2.13"),
    "UD_Indonesian-GSD": ("id_gsd", None),
    # Romance rules wave
    "UD_Galician-CTG": ("gl_ctg", None),
}
SPLITS = ("train", "dev", "test")

UD_DIR = Path(__file__).parent / "data" / "affix_eval" / "ud"
MANIFEST = UD_DIR / "SHA256SUMS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    UD_DIR.mkdir(parents=True, exist_ok=True)
    expected = {}
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            digest, name = line.split(None, 1)
            expected[name.strip()] = digest
    downloaded = kept = 0
    failures = []
    missing_treebanks = []
    for repo, (prefix, tag_override) in sorted(TREEBANKS.items()):
        got_any = False
        tag = tag_override or UD_TAG
        for split in SPLITS:
            name = f"{prefix}-ud-{split}.conllu"
            target = UD_DIR / name
            if not (target.exists() and target.stat().st_size > 0):
                url = (
                    "https://raw.githubusercontent.com/UniversalDependencies/"
                    f"{repo}/{tag}/{name}"
                )
                print(f"fetching {name} ...")
                try:
                    urllib.request.urlretrieve(url, target)
                    downloaded += 1
                    got_any = True
                except OSError as exc:
                    print(f"  skip {name}: {exc}")
                    continue
            else:
                kept += 1
                got_any = True
            if name in expected and sha256(target) != expected[name]:
                failures.append(name)
        if not got_any:
            missing_treebanks.append(prefix)
    # rebuild the manifest so new/updated files are always recorded, while
    # any pre-existing entry's mismatch was already caught above
    MANIFEST.write_text(
        "".join(f"{sha256(p)}  {p.name}\n" for p in sorted(UD_DIR.glob("*.conllu"))),
        encoding="utf-8",
    )
    print(f"done: {kept} kept, {downloaded} downloaded (manifest: {MANIFEST})")
    if missing_treebanks:
        print(f"NO SPLITS FOUND (missing/renamed treebank?): {missing_treebanks}")
    if failures:
        print(f"CHECKSUM MISMATCH: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
