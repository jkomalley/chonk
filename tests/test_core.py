"""Tests for core.py."""

from __future__ import annotations

import os
from pathlib import Path

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

    def __init__(  # noqa: PLR0913
        self,
        *,
        name: str = "fake",
        path: str = "/fake",
        is_dir: bool = False,
        is_file: bool = True,
        is_symlink: bool = False,
        size: int = 0,
        stat_error: OSError | None = None,
        is_symlink_error: OSError | None = None,
    ) -> None:
        self.name = name
        self.path = path
        self._is_dir = is_dir
        self._is_file = is_file
        self._is_symlink = is_symlink
        self._size = size
        self._stat_error = stat_error
        self._is_symlink_error = is_symlink_error

    def is_symlink(self) -> bool:
        if self._is_symlink_error is not None:
            raise self._is_symlink_error
        return self._is_symlink

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:  # noqa: ARG002
        return self._is_dir

    def is_file(self, *, follow_symlinks: bool = True) -> bool:  # noqa: ARG002
        return self._is_file

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:  # noqa: ARG002
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
        Path(entry.path).unlink()
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

    def test_skips_entry_whose_is_symlink_check_raises(self, tmp_path, monkeypatch):
        entries = [
            _FakeEntry(name="a.txt", is_file=True, size=100),
            _FakeEntry(
                name="b.txt",
                is_file=True,
                size=999,
                is_symlink_error=PermissionError("denied"),
            ),
            _FakeEntry(name="c.txt", is_file=True, size=300),
        ]
        monkeypatch.setattr(
            core.os, "scandir", lambda _path: _FakeScandirContext(entries)
        )

        assert core._dir_size(str(tmp_path)) == 400  # a (100) + c (300)

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


class _FakeScandirContext:
    def __init__(self, entries):
        self._entries = entries

    def __enter__(self):
        return iter(self._entries)

    def __exit__(self, *exc_info):
        return False


@pytest.fixture
def tree(tmp_path):
    """A small real directory tree: two files, one hidden file, one subdir.

    Layout: big.bin (3000 B), small.bin (100 B), .hidden (999999 B, excluded),
    sub/nested.bin (500 B). Non-hidden total: 3600 B.
    """
    (tmp_path / "big.bin").write_bytes(b"\0" * 3000)
    (tmp_path / "small.bin").write_bytes(b"\0" * 100)
    (tmp_path / ".hidden").write_bytes(b"\0" * 999999)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.bin").write_bytes(b"\0" * 500)
    return tmp_path


class TestChildSize:
    def test_dispatches_to_dir_size_for_directories(self, tree):
        with os.scandir(tree) as it:
            sub_entry = next(e for e in it if e.name == "sub")
        assert core._child_size(sub_entry) == 500

    def test_dispatches_to_leaf_size_for_files(self, tree):
        with os.scandir(tree) as it:
            file_entry = next(e for e in it if e.name == "big.bin")
        assert core._child_size(file_entry) == 3000


class TestGenerateSizeReport:
    def test_raises_for_missing_path(self, tmp_path):
        missing = tmp_path / "does-not-exist"
        with pytest.raises(ValueError, match="does not exist"):
            core.generate_size_report(missing, min_percent=1.0)

    def test_raises_for_non_directory(self, tmp_path):
        file_path = tmp_path / "file.txt"
        file_path.write_text("x")
        with pytest.raises(ValueError, match="is not a directory"):
            core.generate_size_report(file_path, min_percent=1.0)

    def test_excludes_hidden_and_symlinks(self, tree):
        target = tree / "big.bin"
        (tree / "link").symlink_to(target)

        report = core.generate_size_report(tree, min_percent=0.0)

        assert ".hidden" not in report
        assert "link" not in report
        assert "big.bin" in report

    def test_sorts_descending_and_collapses_small_entries(self, tree):
        report = core.generate_size_report(tree, min_percent=10.0)

        lines = report.splitlines()
        assert "big.bin" in lines[1]  # biggest entry listed first
        assert "<other 1>" in report  # small.bin (2.8%) collapses

    def test_header_reports_correct_total(self, tree):
        report = core.generate_size_report(tree, min_percent=0.0)
        assert f"{tree.absolute()}    3.5 KB" in report

    def test_lists_entries_when_total_is_zero(self, tmp_path):
        (tmp_path / "empty1.txt").touch()
        (tmp_path / "empty2.txt").touch()

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "empty1.txt" in report
        assert "empty2.txt" in report

    def test_tolerates_scandir_failure_on_scan_root(self, tmp_path, monkeypatch):
        def raise_error(_path):
            raise FileNotFoundError(str(tmp_path))

        monkeypatch.setattr(core.os, "scandir", raise_error)

        report = core.generate_size_report(tmp_path, min_percent=1.0)

        assert report == f"{tmp_path.absolute()}    0 B\n"

    def test_does_not_lose_siblings_after_one_entry_errors(self, monkeypatch, tmp_path):
        entries = [
            _FakeEntry(name="a.txt", is_file=True, size=100),
            _FakeEntry(
                name="b.txt", is_file=True, stat_error=PermissionError("denied")
            ),
            _FakeEntry(name="c.txt", is_file=True, size=300),
        ]
        monkeypatch.setattr(
            core.os, "scandir", lambda _path: _FakeScandirContext(entries)
        )

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "a.txt" in report
        assert "c.txt" in report
        assert "400 B" in report  # a (100) + b (0, errored) + c (300)

    def test_does_not_lose_siblings_after_one_entry_is_symlink_errors(
        self, monkeypatch, tmp_path
    ):
        entries = [
            _FakeEntry(name="a.txt", is_file=True, size=100),
            _FakeEntry(
                name="b.txt",
                is_file=True,
                size=999,
                is_symlink_error=PermissionError("denied"),
            ),
            _FakeEntry(name="c.txt", is_file=True, size=300),
        ]
        monkeypatch.setattr(
            core.os, "scandir", lambda _path: _FakeScandirContext(entries)
        )

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "a.txt" in report
        assert "c.txt" in report
        assert "b.txt" not in report  # skipped, not silently kept
        assert "400 B" in report  # a (100) + c (300); b excluded entirely

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are POSIX-only")
    def test_lists_fifo_with_zero_size(self, tmp_path):
        os.mkfifo(tmp_path / "mypipe")

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "mypipe" in report

    def test_sums_multiple_subdirectories_correctly(self, tmp_path):
        for i in range(5):
            sub = tmp_path / f"sub{i}"
            sub.mkdir()
            (sub / "f.bin").write_bytes(b"\0" * 100)

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "500 B" in report  # 5 subdirs x 100 bytes, summed correctly


def test_deliberately_failing_alert_probe() -> None:
    """Temporary: proves the Dependabot failure-alert workflow fires."""
    assert 1 == 2
