"""Subprocess-level smoke tests: confirm dsz works as an installed CLI."""

from __future__ import annotations

import subprocess
import sys


def test_module_invocation_reports_on_given_directory(tmp_path):
    (tmp_path / "f.bin").write_bytes(b"\0" * 10)

    result = subprocess.run(
        [sys.executable, "-m", "dsz", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "f.bin" in result.stdout


def test_module_invocation_exits_1_for_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist"

    result = subprocess.run(
        [sys.executable, "-m", "dsz", str(missing)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "error:" in result.stderr
