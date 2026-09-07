"""Unit tests for contribution density engine."""

from contrigraph.data.density import DensityEngine


def test_density_levels_fixed():
    """Verify fixed density calculation."""
    assert DensityEngine.calculate_fixed_level(0) == 0
    assert DensityEngine.calculate_fixed_level(1) == 1
    assert DensityEngine.calculate_fixed_level(2) == 1
    assert DensityEngine.calculate_fixed_level(3) == 2
    assert DensityEngine.calculate_fixed_level(5) == 2
    assert DensityEngine.calculate_fixed_level(6) == 3
    assert DensityEngine.calculate_fixed_level(10) == 3
    assert DensityEngine.calculate_fixed_level(11) == 4
    assert DensityEngine.calculate_fixed_level(100) == 4


def test_density_github_levels():
    """Verify parsing GitHub GraphQL level strings."""
    assert DensityEngine.parse_github_level("NONE") == 0
    assert DensityEngine.parse_github_level("FIRST_QUARTILE") == 1
    assert DensityEngine.parse_github_level("SECOND_QUARTILE") == 2
    assert DensityEngine.parse_github_level("THIRD_QUARTILE") == 3
    assert DensityEngine.parse_github_level("FOURTH_QUARTILE") == 4
    assert DensityEngine.parse_github_level("UNKNOWN") == 0


def test_adaptive_density_quartiles():
    """Verify adaptive threshold calculation."""
    counts = [1, 2, 2, 4, 5, 8, 12, 15, 20]
    cutoffs = DensityEngine.calculate_quartiles(counts)
    assert len(cutoffs) == 3
    assert cutoffs[0] < cutoffs[1] < cutoffs[2]

    assert DensityEngine.calculate_adaptive_level(0, cutoffs) == 0
    assert DensityEngine.calculate_adaptive_level(1, cutoffs) == 1
    assert DensityEngine.calculate_adaptive_level(25, cutoffs) == 4


def test_adaptive_density_boundary_inclusivity():
    """Verify exact quartile boundary values are inclusive in levels 1, 2, and 3."""
    cutoffs = (1, 5, 20)
    assert DensityEngine.calculate_adaptive_level(0, cutoffs) == 0
    assert DensityEngine.calculate_adaptive_level(1, cutoffs) == 1   # count == q25 must be level 1
    assert DensityEngine.calculate_adaptive_level(2, cutoffs) == 2   # count > q25 and <= q50
    assert DensityEngine.calculate_adaptive_level(5, cutoffs) == 2   # count == q50 must be level 2
    assert DensityEngine.calculate_adaptive_level(6, cutoffs) == 3   # count > q50 and <= q75
    assert DensityEngine.calculate_adaptive_level(20, cutoffs) == 3  # count == q75 must be level 3
    assert DensityEngine.calculate_adaptive_level(21, cutoffs) == 4  # count > q75 must be level 4


def test_adaptive_density_small_and_sparse_datasets():
    """Verify density calculations on small and sparse datasets."""
    # Single element
    cutoffs_single = DensityEngine.calculate_quartiles([1])
    assert DensityEngine.calculate_adaptive_level(1, cutoffs_single) == 1

    # Identical elements
    cutoffs_same = DensityEngine.calculate_quartiles([3, 3, 3, 3])
    assert DensityEngine.calculate_adaptive_level(3, cutoffs_same) == 1

