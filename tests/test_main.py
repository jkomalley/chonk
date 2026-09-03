"""Tests for __main__.py."""

from __future__ import annotations

import importlib

from dsz import cli


def test_module_entry_point_is_the_cli_main():
    # Imported by name rather than at module scope so the import itself --
    # the whole body of __main__.py that `python -m dsz` executes -- runs
    # inside the test and is measured. The subprocess smoke tests in
    # test_cli_subprocess.py exercise the same path but out of process,
    # where coverage cannot see it.
    main_module = importlib.import_module("dsz.__main__")

    assert main_module.main is cli.main
