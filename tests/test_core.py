"""Tests for core.py."""

from __future__ import annotations

import os

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


class _FakeEntry:
    """A minimal os.DirEntry stand-in for testing branches a real DirEntry
    can't be coerced into (a specific stat() failure, a non-regular-file
    type) without depending on OS/filesystem specifics.
    """

    def __init__(
        self,
        *,
        name: str = "fake",
        path: str = "/fake",
        is_dir: bool = False,
        is_file: bool = True,
        is_symlink: bool = False,
        size: int = 0,
        stat_error: OSError | None = None,
    ) -> None:
        self.name = name
        self.path = path
        self._is_dir = is_dir
        self._is_file = is_file
        self._is_symlink = is_symlink
        self._size = size
        self._stat_error = stat_error

    def is_symlink(self) -> bool:
        return self._is_symlink

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:  # noqa: ARG002
        return self._is_dir

    def is_file(self, *, follow_symlinks: bool = True) -> bool:  # noqa: ARG002
        return self._is_file

    def stat(self) -> os.stat_result:
        if self._stat_error is not None:
            raise self._stat_error
        return os.stat_result((0, 0, 0, 0, 0, 0, self._size, 0, 0, 0))


class TestLeafSize:
    def test_returns_file_size(self, tmp_path):
        (tmp_path / "f.bin").write_bytes(b"\0" * 42)
        with os.scandir(tmp_path) as it:
            entry = next(it)
        assert core._leaf_size(entry) == 42

    def test_returns_zero_for_non_regular_file(self):
        entry = _FakeEntry(is_file=False, size=999)
        assert core._leaf_size(entry) == 0

    def test_returns_zero_when_entry_vanishes_before_stat(self, tmp_path):
        (tmp_path / "ephemeral.bin").write_bytes(b"\0" * 10)
        with os.scandir(tmp_path) as it:
            entry = next(it)
        os.remove(entry.path)
        assert core._leaf_size(entry) == 0

    def test_returns_zero_when_stat_raises_permission_error(self):
        entry = _FakeEntry(is_file=True, size=5, stat_error=PermissionError("denied"))
        assert core._leaf_size(entry) == 0


class TestDirSize:
    def test_sums_nested_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "a.bin").write_bytes(b"\0" * 100)
        (sub / "b.bin").write_bytes(b"\0" * 400)
        assert core._dir_size(str(sub)) == 500

    def test_recurses_into_nested_directories(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "f.bin").write_bytes(b"\0" * 77)
        assert core._dir_size(str(tmp_path)) == 77

    def test_skips_symlinks(self, tmp_path):
        target = tmp_path / "target.bin"
        target.write_bytes(b"\0" * 100)
        (tmp_path / "link.bin").symlink_to(target)
        assert core._dir_size(str(tmp_path)) == 100  # not double-counted

    def test_returns_zero_for_unreadable_directory(self, tmp_path, monkeypatch):
        def raise_error(_path):
            raise PermissionError(str(tmp_path))

        monkeypatch.setattr(core.os, "scandir", raise_error)

        assert core._dir_size(str(tmp_path)) == 0

    def test_skips_subdirectory_that_vanishes_mid_walk(self, tmp_path, monkeypatch):
        (tmp_path / "readable.bin").write_bytes(b"\0" * 100)
        vanished = tmp_path / "vanished"
        vanished.mkdir()

        real_scandir = os.scandir

        def flaky_scandir(path):
            if str(path) == str(vanished):
                raise FileNotFoundError(str(path))
            return real_scandir(path)

        monkeypatch.setattr(core.os, "scandir", flaky_scandir)

        assert core._dir_size(str(tmp_path)) == 100
