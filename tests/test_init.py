"""Smoke tests for contrigraph package initialization."""

import contrigraph


def test_package_version():
    """Verify package version is defined."""
    assert contrigraph.__version__ == "0.1.0"


def test_package_exports():
    """Verify package symbols."""
    assert hasattr(contrigraph, "__version__")


def test_cli_package_lazy_exports():
    """Verify contrigraph.cli exports build_parser and callable main cleanly."""
    import contrigraph.cli
    from contrigraph.cli import build_parser, main

    assert callable(main)
    assert callable(build_parser)
    assert callable(contrigraph.cli.main)
    assert callable(contrigraph.cli.build_parser)

    parser = build_parser()
    assert parser.prog == "ghcontrib"

    # Verify invalid attribute raises AttributeError
    import pytest

    with pytest.raises(AttributeError, match="has no attribute 'invalid_attr'"):
        _ = contrigraph.cli.invalid_attr


def test_cli_main_module_execution_no_runtimewarning():
    """Verify executing python -m contrigraph.cli.main emits zero RuntimeWarnings."""
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    res = subprocess.run(
        [sys.executable, "-m", "contrigraph.cli.main", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "RuntimeWarning" not in res.stderr
    assert "usage: ghcontrib" in res.stdout
