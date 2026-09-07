"""Contribution density calculation and quartile engine."""

from typing import Sequence


class DensityEngine:
    """Calculates visual density levels (0-4) for contribution counts."""

    GITHUB_LEVEL_MAP = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }

    @classmethod
    def parse_github_level(cls, level_str: str) -> int:
        """Map GitHub GraphQL level string to integer (0-4)."""
        return cls.GITHUB_LEVEL_MAP.get(level_str.upper(), 0)

    @classmethod
    def calculate_fixed_level(cls, count: int) -> int:
        """Map raw count to standard fixed density tier."""
        if count <= 0:
            return 0
        if count <= 2:
            return 1
        if count <= 5:
            return 2
        if count <= 10:
            return 3
        return 4

    @classmethod
    def calculate_quartiles(cls, counts: Sequence[int]) -> tuple[int, int, int]:
        """Compute quartile cutoffs (q25, q50, q75) for non-zero counts."""
        active = sorted([c for c in counts if c > 0])
        if not active:
            return 1, 2, 3
        n = len(active)
        q25 = active[max(0, int(n * 0.25))]
        q50 = active[max(0, int(n * 0.50))]
        q75 = active[max(0, int(n * 0.75))]

        # Ensure monotonically increasing thresholds
        if q50 <= q25:
            q50 = q25 + 1
        if q75 <= q50:
            q75 = q50 + 1
        return q25, q50, q75

    @classmethod
    def calculate_adaptive_level(cls, count: int, cutoffs: tuple[int, int, int]) -> int:
        """Map count to density level using dynamic quartile thresholds."""
        if count <= 0:
            return 0
        q25, q50, q75 = cutoffs
        if count <= q25:
            return 1
        if count <= q50:
            return 2
        if count <= q75:
            return 3
        return 4
