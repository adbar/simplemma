"""Suffix-table rules shared by the data-driven languages."""

from collections.abc import Container


class SuffixRules:
    """`{target: "suffix suffix ..."}`: the longest suffix found in the table is
    replaced by its target. Leading dots on a suffix are the stem chars it
    needs ("..ante": at least 2); `min_stem` floors every suffix at once.
    `stops` are suffixes that make the rules abstain (no cell fires). The
    remaining keywords are token guards `apply` checks before matching."""

    def __init__(
        self,
        cells: dict[str, str],
        *,
        min_stem: int = 0,
        stops: str = "",
        min_len: int = 1,
        caps: bool = False,
        hyphen: bool = False,
        excluded: Container[str] = frozenset(),
    ) -> None:
        self.cells = cells
        self._table: dict[str, tuple[str | None, int]] = {}
        for target, suffixes in cells.items():
            for suffix in suffixes.split():
                bare = suffix.lstrip(".")
                self._table[bare] = (target, max(min_stem, len(suffix) - len(bare)))
        for suffix in stops.split():
            self._table[suffix] = (None, 0)
        self._min_len, self._caps, self._hyphen = min_len, caps, hyphen
        self._excluded = excluded

    def match(self, token: str) -> tuple[str, str] | None:
        """(suffix, target) of the longest matching suffix; None on a miss or
        stop. Ignores the token guards."""
        for cut in range(len(token)):
            hit = self._table.get(token[cut:])
            if hit is None:
                continue
            target, floor = hit
            if target is None:
                return None
            if cut >= floor:
                return token[cut:], target
        return None

    def apply(self, token: str) -> str | None:
        """The rewritten token, or None (guard tripped, miss or stop)."""
        if (
            len(token) < self._min_len
            or (self._caps and token[:1].isupper())
            or (self._hyphen and "-" in token)
            or token.lower() in self._excluded
        ):
            return None
        found = self.match(token)
        if found is None:
            return None
        suffix, target = found
        return token[: len(token) - len(suffix)] + target
