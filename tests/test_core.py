"""Tests for core.py."""

from __future__ import annotations

import pytest

from dsz import core


class TestFmtSize:
    @pytest.mark.parametrize(
        ("n", "expected"),
        [
            (0, "0 B"),
            (1023, "1023 B"),
            (1024, "1.0 KB"),
            (1048575, "1.0 MB"),  # regression: used to render "1024.0 KB"
            (1024**2, "1.0 MB"),
            (1024**3, "1.0 GB"),
            (1024**4, "1.0 TB"),
            (1024**5, "1.0 PB"),
            (1024**6, "1024.0 PB"),  # PB is the ceiling; no EB tier
        ],
    )
    def test_formats_size(self, n, expected):
        assert core._fmt_size(n) == expected
