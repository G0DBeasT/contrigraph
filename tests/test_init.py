"""Smoke tests for contrigraph package initialization."""

import contrigraph


def test_package_version():
    """Verify package version is defined."""
    assert contrigraph.__version__ == "0.1.0"


def test_package_exports():
    """Verify package symbols."""
    assert hasattr(contrigraph, "__version__")
