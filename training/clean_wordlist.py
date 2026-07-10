"""
Scripted replacement for the semi-manual "eyeball the TSV" clean step between
kaikki_to_tsv.py extraction and dictionary_pickler.py's `_read_dict`.

Scope: language-independent character hygiene ONLY -- NFC-normalize,
canonicalize lookalike quotes, strip invisible/editorial characters, and
reject rows carrying mojibake (U+FFFD) or control/format/surrogate/
private-use/unassigned codepoints. Punctuation/length filtering is
`_read_dict`'s job and is NOT duplicated here. Per-language script filtering
was deliberately removed (measured ~0% yield on clean languages, and wrong
drops of legitimate forms on messy ones) -- do not re-add it.

Input/output: TSV `lemma<TAB>word` per line. Duplicate lines are preserved
verbatim -- R2's evidence-count signal in `dictionary_pickler` depends on line
multiplicity; never dedup here.
"""

import argparse
import json
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Stage 1 normalize: lookalike canonicalization + invisible-char stripping.
LOOKALIKE_MAP = {
    "‘": "'",
    "’": "'",  # curly single quotes -> straight apostrophe
    "“": '"',
    "”": '"',  # curly double quotes -> straight
}
STRIP_CHARS = {
    "﻿",  # BOM
    "­",  # soft hyphen
    "​",  # zero-width space
    "‎",
    "‏",  # LRM/RLM bidi marks (editorial artifacts, not orthography)
}

# Stage 2 reject: codepoint categories never valid in a word form. Format (Cf)
# is included -- stray directional/format chars are junk -- except the two
# word-internal joiners legitimately used mid-word in Perso-Arabic and Indic.
_REJECT_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Cn")
_ALLOWED_FORMAT = {"‌", "‍"}  # ZWNJ, ZWJ

DEFAULT_MAX_REJECT_PCT = 5.0


def normalize(text: str) -> tuple[str, Counter[str]]:
    """Stage 1: fix, don't reject. Returns normalized text + counts for the report."""
    counts: Counter[str] = Counter()
    kept_chars = []
    for ch in unicodedata.normalize("NFC", text):
        if ch in STRIP_CHARS:
            counts[f"stripped_{ch!r}"] += 1
        elif ch in LOOKALIKE_MAP:
            kept_chars.append(LOOKALIKE_MAP[ch])
            counts[f"canonicalized_{ch!r}"] += 1
        else:
            kept_chars.append(ch)
    return "".join(kept_chars), counts


def check_field(text: str) -> str | None:
    """Stage 2: reject unambiguous junk (mojibake / control / format /
    unassigned). Returns a rejection reason or None. No script policy."""
    for ch in text:
        if ch == "�":
            return "replacement_char"  # mojibake tell
        if ch in _ALLOWED_FORMAT:
            continue
        if unicodedata.category(ch) in _REJECT_CATEGORIES:
            return f"control_or_unassigned:{ch!r}"
    return None


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
    """Normalize + junk-reject over raw TSV lines, return kept lines + a report."""
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
            normalized, norm_counts = normalize(column)
            report.normalization_counts.update(norm_counts)
            reason = check_field(normalized)
            if reason:
                report.rejected_by_reason[reason] += 1
                break
            normalized_columns.append(normalized)
        if reason:
            continue
        # A column of only strippable chars (e.g. a lone soft hyphen) survives
        # the raw malformed-line check but normalizes to empty -- don't emit it.
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

    lines = Path(args.input).read_text(encoding="utf-8").splitlines(keepends=True)
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
