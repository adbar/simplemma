"""Language-independent character hygiene shared by the wordlist readers
and writers: NFC, lookalike-quote canonicalization, invisible-char stripping,
and rejecting mojibake/control/unassigned codepoints. Punctuation/length
filtering stays in dictionary_builder. Per-language script filtering was
removed (measured ~0% yield on clean languages, wrong drops on messy ones)
-- do not re-add it.
"""

import unicodedata
from collections.abc import Iterable
from pathlib import Path

from simplemma.utils import normalize_token

# Stage 1: lookalike canonicalization + invisible-char stripping.
LOOKALIKE_MAP = {
    "‘": "'",
    "“": '"',
    "”": '"',
}
# Named escapes, not literals: invisible in an editor/diff.
STRIP_CHARS = {
    "\N{ZERO WIDTH NO-BREAK SPACE}",
    "\N{SOFT HYPHEN}",
    "\N{ZERO WIDTH SPACE}",
    "\N{LEFT-TO-RIGHT MARK}",
    "\N{RIGHT-TO-LEFT MARK}",
}

# Categories never valid in a word form (Cf included except the two
# word-internal joiners allowed below).
_REJECT_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Cn")
_ALLOWED_FORMAT = {"\N{ZERO WIDTH NON-JOINER}", "\N{ZERO WIDTH JOINER}"}


def canonicalize(text: str) -> str:
    """Stage 1: fix, don't reject. Beyond utils.normalize_token (NFC, straight
    apostrophes), this also folds the remaining lookalike quotes and strips
    invisible characters."""
    return "".join(
        LOOKALIKE_MAP.get(ch, ch)
        for ch in normalize_token(text)
        if ch not in STRIP_CHARS
    )


def check_field(text: str) -> str | None:
    """Stage 2: reject unambiguous junk (mojibake/control/format/unassigned).
    Returns a rejection reason or None. No script policy."""
    for ch in text:
        if ch == "�":
            return "replacement_char"
        if ch in _ALLOWED_FORMAT:
            continue
        if unicodedata.category(ch) in _REJECT_CATEGORIES:
            return f"control_or_unassigned:{ch!r}"
    return None


def pair_violation(lemma: str, form: str) -> str | None:
    """Shared validity check for layer-file entries: read_pairs raises on it,
    the mining merge skips on it, so nothing written can crash the load.
    Fields must arrive pre-folded (NFC + canonicalize)."""
    for name, value in (("lemma", lemma), ("form", form)):
        if not value:
            return f"empty {name}"
        reason = check_field(value)
        if reason:
            return f"{name} {value!r} rejected ({reason})"
    return None


def read_pairs(path: Path) -> dict[str, str]:
    """Strictly load a curated ``lemma<TAB>form`` file into a form->lemma dict.

    For reviewed artifacts (overrides), NOT bulk wordlists: corruption is
    an ERROR, not a silently-dropped row. Raises ValueError on a malformed
    row, empty/mojibake field, or a form mapped to two different lemmas.
    Blank lines and exact-duplicate pairs are harmless and skipped/kept once."""
    mapping: dict[str, str] = {}
    with open(path, encoding="utf-8") as filehandle:
        for line_no, line in enumerate(filehandle, start=1):
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            parts = stripped.split("\t")
            if len(parts) != 2:
                raise ValueError(
                    f"{path}:{line_no}: expected 'lemma<TAB>form', got {stripped!r}"
                )
            lemma, form = (normalize_token(part) for part in parts)
            reason = pair_violation(lemma, form)
            if reason:
                raise ValueError(f"{path}:{line_no}: {reason} in {stripped!r}")
            if mapping.setdefault(form, lemma) != lemma:
                raise ValueError(
                    f"{path}:{line_no}: form {form!r} maps to both "
                    f"{mapping[form]!r} and {lemma!r}"
                )
    return mapping


def write_pairs(pairs: Iterable[tuple[str, str]], path: Path) -> int:
    """Write ``lemma<TAB>form`` lines to `path`, returning the pair count."""
    count = 0
    with open(path, "w", encoding="utf-8") as filehandle:
        for lemma, form in pairs:
            filehandle.write(f"{lemma}\t{form}\n")
            count += 1
    return count
