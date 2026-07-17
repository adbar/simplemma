"""Format/integrity guard for the shipped override lexicons in training/overrides/{lang}.tsv:
these are reviewed artifacts, so a corrupting hand-edit must fail CI, not silently ship."""

from pathlib import Path

import pytest

from training.clean_wordlist import read_pairs

OVERRIDES_DIR = Path(__file__).parent.parent / "training" / "overrides"
OVERRIDE_FILES = sorted(OVERRIDES_DIR.glob("*.tsv"))


def test_at_least_one_override_shipped():
    assert OVERRIDE_FILES, f"no override files found in {OVERRIDES_DIR}"


@pytest.mark.parametrize("path", OVERRIDE_FILES, ids=lambda p: p.stem)
def test_override_file_reads_cleanly(path):
    """read_pairs enforces well-formedness, NFC, no empty/junk field, no conflicting form."""
    assert read_pairs(path), f"{path} is empty"
