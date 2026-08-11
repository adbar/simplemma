"""Scripted replacement for the manual "eyeball the TSV" clean step between
kaikki_to_tsv.py extraction and dictionary_builder.py's `_read_dict`.

Scope: language-independent character hygiene ONLY -- NFC, lookalike-quote
canonicalization, invisible-char stripping, and rejecting mojibake/control/
unassigned codepoints. Punctuation/length filtering stays in `_read_dict`.
Per-language script filtering was removed (measured ~0% yield on clean
languages, wrong drops on messy ones) -- do not re-add it.

Duplicate lines are preserved verbatim -- dictionary_builder's evidence-count
signal depends on line multiplicity; never dedup here.
"""

import argparse
import json
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from simplemma.utils import normalize_token

# Stage 1: lookalike canonicalization + invisible-char stripping.
LOOKALIKE_MAP = {
    "‘": "'",
    "’": "'",
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

DEFAULT_MAX_REJECT_PCT = 5.0


def canonicalize(text: str) -> tuple[str, Counter[str]]:
    """Stage 1: fix, don't reject. Unlike utils.normalize_token (NFC only),
    this also folds lookalike quotes and strips invisible characters."""
    counts: Counter[str] = Counter()
    kept_chars = []
    for ch in normalize_token(text):
        if ch in STRIP_CHARS:
            counts[f"stripped_{ch!r}"] += 1
        elif ch in LOOKALIKE_MAP:
            kept_chars.append(LOOKALIKE_MAP[ch])
            counts[f"canonicalized_{ch!r}"] += 1
        else:
            kept_chars.append(ch)
    return "".join(kept_chars), counts


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

    For reviewed artifacts (overrides/fill), NOT bulk wordlists: corruption is
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
            if form in mapping and mapping[form] != lemma:
                raise ValueError(
                    f"{path}:{line_no}: form {form!r} maps to both "
                    f"{mapping[form]!r} and {lemma!r}"
                )
            mapping[form] = lemma
    return mapping


def write_pairs(pairs: Iterable[tuple[str, str]], path: Path) -> int:
    """Write ``lemma<TAB>form`` lines to `path`, returning the pair count."""
    count = 0
    with open(path, "w", encoding="utf-8") as filehandle:
        for lemma, form in pairs:
            filehandle.write(f"{lemma}\t{form}\n")
            count += 1
    return count


@dataclass
class CleanReport:
    total: int = 0
    kept: int = 0
    rejected_by_reason: Counter[str] = field(default_factory=Counter)
    normalization_counts: Counter[str] = field(default_factory=Counter)

    @property
    def reject_pct(self) -> float:
        return 100.0 * (self.total - self.kept) / self.total if self.total else 0.0

    def to_json(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "kept": self.kept,
            "reject_pct": round(self.reject_pct, 2),
            "rejected_by_reason": dict(self.rejected_by_reason),
            "normalization_counts": dict(self.normalization_counts),
        }


def clean_wordlist(lines: list[str]) -> tuple[list[str], CleanReport]:
    """Normalize + junk-reject raw TSV lines, return kept lines + a report."""
    report = CleanReport()
    kept_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        report.total += 1

        columns = line.split("\t")
        if len(columns) != 2 or not columns[0] or not columns[1]:
            report.rejected_by_reason["malformed_line"] += 1
            continue

        normalized_columns = []
        reason = None
        for column in columns:
            normalized, norm_counts = canonicalize(column)
            report.normalization_counts.update(norm_counts)
            reason = check_field(normalized)
            if reason:
                report.rejected_by_reason[reason] += 1
                break
            normalized_columns.append(normalized)
        if reason:
            continue
        # a column of only strippable chars normalizes to empty -- don't emit it
        if not all(normalized_columns):
            report.rejected_by_reason["empty_after_normalize"] += 1
            continue

        report.kept += 1
        kept_lines.append("\t".join(normalized_columns))

    return kept_lines, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Raw TSV path (lemma<TAB>word per line)")
    parser.add_argument("output", help="Cleaned TSV output path")
    parser.add_argument(
        "--report", help="JSON report path (default: <output>.report.json)"
    )
    parser.add_argument("--max-reject-pct", type=float, default=DEFAULT_MAX_REJECT_PCT)
    args = parser.parse_args()

    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    kept_lines, report = clean_wordlist(lines)

    Path(args.output).write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    report_path = (
        Path(args.report) if args.report else Path(f"{args.output}.report.json")
    )
    report_path.write_text(json.dumps(report.to_json(), indent=2, ensure_ascii=False))

    print(
        f"kept {report.kept}/{report.total} "
        f"({100 - report.reject_pct:.2f}%), rejected {report.reject_pct:.2f}%"
    )
    for reason, count in report.rejected_by_reason.most_common(5):
        print(f"  {reason}: {count}")

    if report.reject_pct > args.max_reject_pct:
        print(
            f"ERROR: reject rate {report.reject_pct:.2f}% exceeds "
            f"max-reject-pct={args.max_reject_pct} -- possible data drift",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
