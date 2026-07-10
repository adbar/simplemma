"""
Format/integrity guard for the shipped closed-class override lexicons in
training/overrides/{lang}.tsv (see build_override.py for how they were
derived and validated). These are real, reviewed artifacts now -- not
throwaway script output -- so a future hand-edit that corrupts one should
fail CI, not silently ship.
"""

from pathlib import Path

import pytest

OVERRIDES_DIR = Path(__file__).parent.parent / "training" / "overrides"
OVERRIDE_FILES = sorted(OVERRIDES_DIR.glob("*.tsv"))


def test_at_least_one_override_shipped():
    assert OVERRIDE_FILES, f"no override files found in {OVERRIDES_DIR}"


@pytest.mark.parametrize("path", OVERRIDE_FILES, ids=lambda p: p.stem)
def test_override_file_is_well_formed(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines, f"{path} is empty"
    for line in lines:
        columns = line.split("\t")
        assert len(columns) == 2, f"{path}: expected 2 columns, got {columns!r}"
        lemma, form = columns
        assert lemma and form, f"{path}: empty field in {columns!r}"


@pytest.mark.parametrize("path", OVERRIDE_FILES, ids=lambda p: p.stem)
def test_override_file_has_no_conflicting_forms(path):
    """The same form mapping to two different lemmas within one override
    file would silently pick whichever line dict.update() sees last."""
    seen: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        lemma, form = line.split("\t")
        if form in seen and seen[form] != lemma:
            pytest.fail(f"{path}: {form!r} maps to both {seen[form]!r} and {lemma!r}")
        seen[form] = lemma
