"""
Format/integrity guard for the shipped closed-class override lexicons in
training/overrides/{lang}.tsv (see build_override.py for how they were
derived and validated). These are real, reviewed artifacts now -- not
throwaway script output -- so a future hand-edit that corrupts one should
fail CI, not silently ship.
"""

from pathlib import Path

import pytest

from training.clean_wordlist import read_pairs

OVERRIDES_DIR = Path(__file__).parent.parent / "training" / "overrides"
OVERRIDE_FILES = sorted(OVERRIDES_DIR.glob("*.tsv"))


def test_at_least_one_override_shipped():
    assert OVERRIDE_FILES, f"no override files found in {OVERRIDES_DIR}"


@pytest.mark.parametrize("path", OVERRIDE_FILES, ids=lambda p: p.stem)
def test_override_file_reads_cleanly(path):
    """read_pairs is the shared strict reader: it enforces well-formedness, NFC,
    no empty/junk field, and no conflicting duplicate form. A corrupt hand-edit
    fails here rather than silently shipping."""
    assert read_pairs(path), f"{path} is empty"
