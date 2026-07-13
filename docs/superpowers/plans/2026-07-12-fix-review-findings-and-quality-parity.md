# Fix Review Findings and Quality Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 15 findings from the max-effort code review of `dsz`, and bring the project's tooling/testing/docs up to a quality bar similar to the sibling project `~/code/envbool`, scaled down for a ~150-line CLI tool.

**Architecture:** `core.py`'s two independently-written directory-scanning implementations (the root cause of most of the review's bugs) are consolidated around two small, individually-testable primitives — `_leaf_size()` (one file/other-entry) and `_dir_size()` (one subtree, iterative) — both of which treat every filesystem race (entry deleted or made unreadable mid-scan) as "contributes 0 bytes," never as "crash" or "silently vanish." `generate_size_report()` scans immediate children concurrently via `ThreadPoolExecutor`. `cli.py` gains input validation and a broadened error boundary. The project gains `ty` type checking, `ruff` linting (`ALL` rules + documented ignores), a real pytest suite using `tmp_path` for real-filesystem tests and small duck-typed stubs for hard-to-reach error branches, a `justfile`, pre-commit hooks, a CI workflow, and a `CLAUDE.md`.

**Tech Stack:** Python 3.11+, `uv` (packaging/dependency management), `pytest` (testing), `ruff` (lint + format), `ty` (type checking), `pre-commit`, GitHub Actions.

## Global Constraints

- `requires-python = ">=3.11"` (widened from the review-flagged `>=3.14`; nothing in this codebase needs 3.14).
- No new runtime dependencies — `dependencies = []` stays empty; stdlib only (`ThreadPoolExecutor` is stdlib).
- Dev dependencies: `pytest`, `pytest-cov`, `ruff`, `ty`, `pre-commit`. No `hypothesis`.
- No hard 100%-coverage CI gate. Aim for thorough, realistic coverage; don't chase the last percent artificially.
- Google-style docstrings, `ruff` with `select = ["ALL"]` plus documented, justified ignores, 88-char line length, full type hints checked by `ty`.
- No `CONTRIBUTING.md`, `CHANGELOG.md`, or semver version-guard CI job — this is a lean personal-utility setup, not a public-library contribution workflow.
- Do not modify `.github/workflows/pypi.yml` or `.github/workflows/testpypi.yml` — they stay as manual-dispatch publish workflows.
- The `LICENSE` file (MIT, already present) does not need to change; only `pyproject.toml`'s `license` field is added.
- **The single most important invariant across every task that touches scanning logic:** a filesystem race (entry deleted or made unreadable between being listed and being examined) must make that entry contribute 0 bytes — it must never raise an uncaught exception, and it must never silently disappear from the listing.

---

## Task 1: Project tooling and packaging metadata

**Files:**
- Modify: `pyproject.toml`
- Create: `src/dsz/py.typed`
- Create: `justfile`
- Create: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a `uv sync`-able dev environment with `pytest`, `pytest-cov`, `ruff`, `ty`, `pre-commit` installed; `just <task>` commands available to every later task's verification steps.

- [ ] **Step 1: Rewrite `pyproject.toml`**

Replace the entire file with:

```toml
[project]
name = "dsz"
version = "0.1.0"
description = "Show disk usage of a directory's immediate children."
readme = "README.md"
authors = [{ name = "Kyle O'Malley", email = "j.kyle.omalley@gmail.com" }]
requires-python = ">=3.11"
license = "MIT"
keywords = ["disk usage", "du", "cli", "filesystem"]
dependencies = []
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "Topic :: System :: Filesystems",
    "Topic :: Utilities",
    "Environment :: Console",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Typing :: Typed",
]

[project.urls]
Homepage = "https://github.com/jkomalley/dsz"
Repository = "https://github.com/jkomalley/dsz"
Issues = "https://github.com/jkomalley/dsz/issues"

[project.scripts]
dsz = "dsz.cli:main"

[build-system]
requires = ["uv_build>=0.11.16,<0.12.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pre-commit>=4.5.1",
    "pytest>=9.0.3",
    "pytest-cov>=7.1.0",
    "ruff>=0.15.10",
    "ty>=0.0.29",
]

# --------------------------------------------------------------------------- #
# Ruff
# --------------------------------------------------------------------------- #
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = ["ALL"]
ignore = [
    # --- Formatting / style clashes ---
    "D203",   # one-blank-line-before-class (conflicts with D211)
    "D213",   # multi-line-summary-second-line (conflicts with D212)
    "D100",   # missing docstring in public module
    "D104",   # missing docstring in public package
    "D107",   # missing docstring in __init__ method

    # --- Overly pedantic / noisy ---
    "COM812", # missing trailing comma (conflicts with formatter)
    "ISC001", # single-line implicit string concatenation (conflicts with formatter)
    "FIX002", # line contains TODO
    "TD002",  # missing author in TODO
    "TD003",  # missing issue link in TODO
    "ERA001", # found commented-out code
    "TRY003", # avoid specifying long messages outside the exception class
    "EM101",  # exception must not use a string literal
    "EM102",  # exception must not use an f-string literal

    # --- Pragmatic ignores ---
    "S101",   # use of assert (needed in tests, fine in internal code)
    "PLR2004",# magic value used in comparison
    "CPY001", # missing copyright notice
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "D",      # no docstring requirements in tests
    "ANN",    # no type annotation requirements in tests
    "SLF001", # allow access to private members in tests
]
"src/dsz/cli.py" = [
    "T201",   # print() is the primary output mechanism for CLI
]

# --------------------------------------------------------------------------- #
# ty
# --------------------------------------------------------------------------- #
[tool.ty.rules]
possibly-missing-import = "warn"

# --------------------------------------------------------------------------- #
# Pytest
# --------------------------------------------------------------------------- #
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
]

# --------------------------------------------------------------------------- #
# Coverage
# --------------------------------------------------------------------------- #
[tool.coverage.run]
source = ["dsz"]
branch = true

[tool.coverage.report]
show_missing = true
skip_empty = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
]
```

Note: the dev-dependency version floors above match what's already resolving cleanly for the sibling `envbool` project on this machine. If `uv sync` reports one is unavailable, loosen that one floor and retry — don't loosen the others speculatively.

- [ ] **Step 2: Add the `py.typed` marker**

Create an empty file at `src/dsz/py.typed` (zero bytes — its mere presence is what matters, per PEP 561).

- [ ] **Step 3: Create the `justfile`**

```just
# Run all checks
all: format lint typecheck test

# Format code
format:
    uv run ruff format src/ tests/

# Lint code
lint:
    uv run ruff check src/ tests/

# Type check
typecheck:
    uv run ty check src/

# Run tests
test:
    uv run pytest

# Run tests with coverage
cov:
    uv run pytest --cov=dsz
```

- [ ] **Step 4: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.10
    hooks:
      - id: ruff-format
      - id: ruff
        args: [--fix]

  - repo: local
    hooks:
      - id: ty
        name: ty type check
        entry: uv run ty check src/
        language: system
        pass_filenames: false
        stages: [pre-push]

      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        pass_filenames: false
        stages: [pre-push]
```

- [ ] **Step 5: Sync dependencies and verify**

Run: `uv sync`
Expected: completes without error; creates/updates `uv.lock` and `.venv`.

Note: `just lint` and `just typecheck` are **not** expected to pass yet — the existing `core.py`/`cli.py` predate `ruff`'s `ALL` ruleset and will show violations until Tasks 2–6 rewrite them. That's expected; don't try to fix lint findings in this task.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/dsz/py.typed justfile .pre-commit-config.yaml uv.lock
git commit -m "chore: add dev tooling (ruff, ty, pytest, pre-commit, justfile)"
```

---

## Task 2: Fix `_fmt_size` (rounding-boundary bug, add TB/PB tiers)

**Files:**
- Modify: `src/dsz/core.py`
- Test: `tests/test_core.py` (new file)

**Interfaces:**
- Consumes: nothing new.
- Produces: `_fmt_size(n: int) -> str` in `src/dsz/core.py` — same signature as before; fixes review findings #7 (`"1024.0 KB"` display bug) and #8 (no TB/PB tier).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_core.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/kyle/code/dsz && uv run pytest tests/test_core.py -v`
Expected: FAIL — `1048575` renders as `"1024.0 KB"` (not `"1.0 MB"`), and `1024**4`/`1024**5` fail since there's no TB/PB tier yet.

- [ ] **Step 3: Rewrite `_fmt_size` in `src/dsz/core.py`**

Replace the file's contents up through the old `_fmt_size` function (keep everything from `_dir_size` onward unchanged for now — that's Task 3's job):

```python
"""dsz scan module."""

from pathlib import Path
import os


_UNITS: tuple[str, ...] = ("KB", "MB", "GB", "TB", "PB")


def _fmt_size(n: int) -> str:
    """Format a byte count as a human-readable string.

    Args:
        n: A non-negative byte count.

    Returns:
        The size formatted with the largest unit that keeps the displayed,
        rounded value under 1024 (e.g. "512 B", "1.5 MB"), capped at "PB".
    """
    if n < 1024:
        return f"{n} B"

    size = float(n)
    unit = _UNITS[0]
    for unit in _UNITS:
        size /= 1024
        # Compare the *rounded* value against 1024, not the raw value --
        # otherwise a size that rounds up to "1024.0 KB" at display time
        # (e.g. 1048575 bytes) would stop one unit too early.
        if round(size, 1) < 1024 or unit == _UNITS[-1]:
            break

    return f"{size:.1f} {unit}"
```

(Leave `_dir_size` and `generate_size_report` exactly as they were below this point — they're rewritten in Tasks 3–5.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_core.py -v`
Expected: PASS (all 9 parametrized cases).

- [ ] **Step 5: Commit**

```bash
git add src/dsz/core.py tests/test_core.py
git commit -m "fix: correct _fmt_size rounding-boundary bug and add TB/PB tiers"
```

---

## Task 3: Consolidate entry-sizing into `_leaf_size` + rewrite `_dir_size`

**Files:**
- Modify: `src/dsz/core.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: `_fmt_size(n: int) -> str` (Task 2, unused directly here but stays in the file).
- Produces: `_leaf_size(entry: os.DirEntry[str]) -> int` (new) and `_dir_size(path: str) -> int` (rewritten, same signature) in `src/dsz/core.py`. Fixes review finding #2 (`_dir_size`'s `os.scandir` call only caught `PermissionError`, not `OSError`).

- [ ] **Step 1: Write the failing tests**

First, add `import os` to the top import block of `tests/test_core.py` (it's needed by the new tests below for `os.scandir`/`os.stat_result`/`os.remove`). The top of the file should read:

```python
"""Tests for core.py."""

from __future__ import annotations

import os

import pytest

from dsz import core
```

Then append the following to the end of `tests/test_core.py` (below the existing `TestFmtSize` class — do not repeat the `import os` here, it only goes in the top block above):

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_core.py -v`
Expected: FAIL with `AttributeError: module 'dsz.core' has no attribute '_leaf_size'`, and the `test_skips_subdirectory_that_vanishes_mid_walk` test fails with an unhandled `FileNotFoundError` against the current `_dir_size` (it only catches `PermissionError` around `os.scandir`).

- [ ] **Step 3: Rewrite `_dir_size` and add `_leaf_size` in `src/dsz/core.py`**

Replace everything from `def _dir_size` through the end of that function with:

```python
def _leaf_size(entry: os.DirEntry[str]) -> int:
    """Return a non-directory, non-symlink entry's byte size.

    Args:
        entry: A scandir entry already confirmed to not be a symlink.

    Returns:
        The entry's byte size if it's a regular file; 0 for other entry
        types (FIFOs, sockets, device files), which don't have a
        meaningful "disk usage" figure to sum. Also returns 0 if the
        entry vanishes or becomes unreadable between being listed and
        being stat'd here -- a race under concurrent filesystem activity
        -- so one bad entry doesn't abort the scan of its siblings.
    """
    try:
        stat = entry.stat()
    except OSError:
        return 0
    return stat.st_size if entry.is_file(follow_symlinks=False) else 0


def _dir_size(path: str) -> int:
    """Return the total byte size of all files under path.

    Args:
        path: Directory to scan, recursively.

    Returns:
        The sum of every regular file's size under path. Symlinks are
        skipped. Directories that can't be listed (permission denied,
        removed mid-scan) contribute 0 rather than raising, so one
        unreadable subtree doesn't abort the rest of the scan.
    """
    total_size = 0
    stack = [path]

    while stack:
        current = stack.pop()
        try:
            dir_iter_ctx = os.scandir(current)
        except OSError:
            continue

        with dir_iter_ctx as dir_iter:
            for entry in dir_iter:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                else:
                    total_size += _leaf_size(entry)

    return total_size
```

Also add `from __future__ import annotations` as the first import in the file (needed so the `os.DirEntry[str]` annotation above is never evaluated at runtime — it's only used by `ty`), and move the `Path` import under a `TYPE_CHECKING` guard since it's now used only in annotations:

```python
"""dsz scan module."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
```

(This replaces the file's original `from pathlib import Path` / `import os` pair at the top.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_core.py -v`
Expected: PASS (all `TestFmtSize`, `TestLeafSize`, `TestDirSize` cases).

- [ ] **Step 5: Commit**

```bash
git add src/dsz/core.py tests/test_core.py
git commit -m "fix: make _dir_size tolerate OSError (not just PermissionError) on scandir races"
```

---

## Task 4: Rewrite `generate_size_report` (correctness fixes, sequential)

**Files:**
- Modify: `src/dsz/core.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: `_fmt_size` (Task 2), `_leaf_size`/`_dir_size` (Task 3).
- Produces: `_child_size(entry: os.DirEntry[str]) -> int` (new) and `generate_size_report(path: Path, min_percent: float) -> str` (rewritten, same signature) in `src/dsz/core.py`. Fixes review findings #1 (unguarded top-level `entry.stat()`), #3 (top-level `os.scandir` race), #5 (silent sibling-drop), #6 (FIFOs/sockets silently excluded), #9 (all-zero-byte directory hides entries), plus cleanup findings #11 (duplicated scan logic), #12 (redundant bar/percent ratio), and the sort-key idiom cleanup.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core.py`:

```python
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

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs are POSIX-only")
    def test_lists_fifo_with_zero_size(self, tmp_path):
        os.mkfifo(tmp_path / "mypipe")

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "mypipe" in report
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_core.py -v`
Expected: FAIL — `_child_size` doesn't exist yet; `test_lists_entries_when_total_is_zero` fails against the current early-return; `test_tolerates_scandir_failure_on_scan_root` fails with an unhandled `FileNotFoundError`; `test_does_not_lose_siblings_after_one_entry_errors` fails because a `PermissionError` on `b.txt` currently aborts the whole loop.

- [ ] **Step 3: Rewrite `generate_size_report` in `src/dsz/core.py`**

Replace everything from `def generate_size_report` to the end of the file with:

```python
def _child_size(entry: os.DirEntry[str]) -> int:
    """Return an immediate child's byte size: itself, or its subtree total.

    Args:
        entry: A scandir entry already confirmed to not be hidden or a
            symlink.

    Returns:
        `_dir_size(entry.path)` for a directory, `_leaf_size(entry)`
        otherwise.
    """
    if entry.is_dir(follow_symlinks=False):
        return _dir_size(entry.path)
    return _leaf_size(entry)


def generate_size_report(path: Path, min_percent: float) -> str:
    """Scan path's immediate children and return a formatted size report string.

    Args:
        path: Directory to scan.
        min_percent: Entries below this percentage of the total are
            collapsed into a single "<other N>" line.

    Returns:
        A header line ("<absolute path>    <total size>") followed by one
        line per child at or above min_percent, sorted by size descending,
        with a trailing "<other N>" line for anything collapsed. Hidden
        entries (leading dot) and symlinks are excluded entirely. Other
        filesystem object types (FIFOs, sockets, device files) are listed
        but always contribute 0 bytes.

    Raises:
        ValueError: If path does not exist or is not a directory.
    """
    if not path.exists():
        msg = f"path '{path}' does not exist"
        raise ValueError(msg)

    if not path.is_dir():
        msg = f"path '{path}' is not a directory"
        raise ValueError(msg)

    try:
        with os.scandir(path) as dir_iter:
            children = [
                entry
                for entry in dir_iter
                if not entry.name.startswith(".") and not entry.is_symlink()
            ]
    except OSError:
        # Unreadable or vanished directory: report a total of 0 rather than
        # raising -- path was just confirmed to exist and be a directory
        # above, so this is a race, not a usage error.
        children = []

    entries = {entry.name: _child_size(entry) for entry in children}
    total_size = sum(entries.values())

    out_lines = [f"{path.absolute()}    {_fmt_size(total_size)}"]

    if not entries:
        return "\n".join(out_lines) + "\n"

    sorted_entries = sorted(entries.items(), key=lambda item: item[1], reverse=True)

    above: list[tuple[str, int, float]] = []
    below: list[tuple[str, int, float]] = []
    for name, size in sorted_entries:
        percent = (size / total_size * 100) if total_size else 0.0
        (above if percent >= min_percent else below).append((name, size, percent))

    for name, size, percent in above:
        bar = "#" * round(percent / 5)
        out_lines.append(f"{_fmt_size(size):>10} {percent:>3.0f}% {name:<20} {bar}")

    if below:
        other_size = sum(size for _, size, _ in below)
        other_percent = (other_size / total_size * 100) if total_size else 0.0
        other_count = len(below)
        bar = "#" * round(other_percent / 5)
        other_label = f"<other {other_count}>"
        out_lines.append(
            f"{_fmt_size(other_size):>10} {other_percent:>3.0f}% "
            f"{other_label:<20} {bar}"
        )

    return "\n".join(out_lines) + "\n"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_core.py -v`
Expected: PASS (all cases, including the previously-failing ones above).

- [ ] **Step 5: Commit**

```bash
git add src/dsz/core.py tests/test_core.py
git commit -m "fix: consolidate top-level scan onto _child_size, fix zero-byte and FIFO handling"
```

---

## Task 5: Parallelize `generate_size_report`'s top-level scan

**Files:**
- Modify: `src/dsz/core.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: `_child_size(entry: os.DirEntry[str]) -> int` (Task 4).
- Produces: `generate_size_report` unchanged in signature and observable behavior; internals now use `ThreadPoolExecutor`. Fixes review finding #(efficiency) — sequential subdirectory scanning left concurrency on the table.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_core.py` (inside `TestGenerateSizeReport`... add as a new test at the end of that class):

```python
    def test_sums_multiple_subdirectories_correctly(self, tmp_path):
        for i in range(5):
            sub = tmp_path / f"sub{i}"
            sub.mkdir()
            (sub / "f.bin").write_bytes(b"\0" * 100)

        report = core.generate_size_report(tmp_path, min_percent=0.0)

        assert "500 B" in report  # 5 subdirs x 100 bytes, summed correctly
```

This test alone won't distinguish sequential from concurrent execution (both would pass) — its purpose is a correctness regression guard for the refactor in Step 3. The real verification for this task is that the **entire existing** `tests/test_core.py` suite still passes unchanged after switching to threading, especially `test_does_not_lose_siblings_after_one_entry_errors` (Task 4) — that test must keep passing under real thread execution, not just sequential execution.

- [ ] **Step 2: Run the tests to verify the new test passes already (sequential) and note the baseline**

Run: `uv run pytest tests/test_core.py -v`
Expected: PASS — this confirms the correctness baseline before the concurrency refactor, so any regression introduced by Step 3 is attributable to that change.

- [ ] **Step 3: Switch the top-level scan to `ThreadPoolExecutor`**

In `src/dsz/core.py`, add the import at the top of the file (alongside the existing `import os`):

```python
from concurrent.futures import ThreadPoolExecutor
```

Then, in `generate_size_report`, replace:

```python
    entries = {entry.name: _child_size(entry) for entry in children}
    total_size = sum(entries.values())
```

with:

```python
    with ThreadPoolExecutor() as pool:
        sizes = list(pool.map(_child_size, children))

    entries = dict(zip((c.name for c in children), sizes, strict=True))
    total_size = sum(sizes)
```

- [ ] **Step 4: Run the full test suite to verify no regressions**

Run: `uv run pytest tests/test_core.py -v`
Expected: PASS — every test from Tasks 2–5, including `test_does_not_lose_siblings_after_one_entry_errors`, still passes with the threaded implementation.

- [ ] **Step 5: Commit**

```bash
git add src/dsz/core.py tests/test_core.py
git commit -m "perf: scan immediate children concurrently with ThreadPoolExecutor"
```

---

## Task 6: Rewrite `cli.py` (validation, error handling) and add `__main__.py`

**Files:**
- Modify: `src/dsz/cli.py`
- Create: `src/dsz/__main__.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_cli_subprocess.py`

**Interfaces:**
- Consumes: `generate_size_report(path: Path, min_percent: float) -> str` (Task 5).
- Produces: `_percent(raw: str) -> float`, `_build_parser() -> argparse.ArgumentParser`, `main() -> None` in `src/dsz/cli.py`. Fixes review finding #4 (broaden `except ValueError` to also catch `OSError`) and #10 (`--min-percent nan` silently collapsing everything).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli.py`:

```python
"""Tests for cli.py: _percent, _build_parser, and main()."""

from __future__ import annotations

import argparse

import pytest

from dsz import cli


class TestPercent:
    def test_accepts_valid_value(self):
        assert cli._percent("42.5") == 42.5

    def test_accepts_boundary_values(self):
        assert cli._percent("0") == 0.0
        assert cli._percent("100") == 100.0

    def test_rejects_non_numeric(self):
        with pytest.raises(argparse.ArgumentTypeError):
            cli._percent("not-a-number")

    def test_rejects_nan(self):
        with pytest.raises(argparse.ArgumentTypeError):
            cli._percent("nan")

    def test_rejects_negative(self):
        with pytest.raises(argparse.ArgumentTypeError):
            cli._percent("-1")

    def test_rejects_above_100(self):
        with pytest.raises(argparse.ArgumentTypeError):
            cli._percent("100.1")


class TestBuildParser:
    def test_defaults(self):
        args = cli._build_parser().parse_args([])
        assert str(args.PATH) == "."
        assert args.min_percent == 1.0

    def test_parses_path_and_min_percent(self, tmp_path):
        args = cli._build_parser().parse_args([str(tmp_path), "--min-percent", "5"])
        assert str(args.PATH) == str(tmp_path)
        assert args.min_percent == 5.0

    def test_rejects_invalid_min_percent(self):
        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["--min-percent", "nan"])


class TestMain:
    def test_prints_report_for_valid_directory(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "f.bin").write_bytes(b"\0" * 10)
        monkeypatch.setattr("sys.argv", ["dsz", str(tmp_path)])

        cli.main()

        out = capsys.readouterr().out
        assert str(tmp_path.absolute()) in out
        assert "f.bin" in out

    def test_exits_1_with_clean_message_for_missing_path(
        self, tmp_path, monkeypatch, capsys
    ):
        missing = tmp_path / "does-not-exist"
        monkeypatch.setattr("sys.argv", ["dsz", str(missing)])

        with pytest.raises(SystemExit) as exc_info:
            cli.main()

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "error:" in err
        assert "does not exist" in err

    def test_exits_1_with_clean_message_for_non_directory(
        self, tmp_path, monkeypatch, capsys
    ):
        file_path = tmp_path / "file.txt"
        file_path.write_text("x")
        monkeypatch.setattr("sys.argv", ["dsz", str(file_path)])

        with pytest.raises(SystemExit) as exc_info:
            cli.main()

        assert exc_info.value.code == 1
        assert "is not a directory" in capsys.readouterr().err
```

Create `tests/test_cli_subprocess.py`:

```python
"""Subprocess-level smoke tests: confirm dsz works as an installed CLI."""

from __future__ import annotations

import subprocess
import sys


def test_module_invocation_reports_on_current_directory(tmp_path):
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cli.py tests/test_cli_subprocess.py -v`
Expected: FAIL — `cli._percent` and `cli._build_parser` don't exist yet (`main()` currently builds the parser inline); the subprocess tests fail with `No module named dsz.__main__`.

- [ ] **Step 3: Rewrite `src/dsz/cli.py`**

Replace the entire file:

```python
"""dsz CLI -- show disk usage of a directory's immediate children.

Public surface:
    main()  -- entry point registered as the "dsz" command
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from dsz.core import generate_size_report


def _percent(raw: str) -> float:
    """Parse and validate a --min-percent value.

    Args:
        raw: The raw command-line argument string.

    Returns:
        The parsed value, guaranteed to be a finite number in [0, 100].

    Raises:
        argparse.ArgumentTypeError: If raw isn't a finite number in [0, 100].
    """
    try:
        value = float(raw)
    except ValueError as e:
        msg = f"invalid float value: {raw!r}"
        raise argparse.ArgumentTypeError(msg) from e
    if math.isnan(value) or not 0 <= value <= 100:
        msg = f"--min-percent must be between 0 and 100, got {raw!r}"
        raise argparse.ArgumentTypeError(msg)
    return value


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Show disk usage of a directory's immediate children."
    )
    parser.add_argument(
        "PATH",
        nargs="?",
        default=".",
        type=Path,
        help="directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--min-percent",
        default=1.0,
        metavar="N",
        type=_percent,
        help="collapse entries below N%% of total into one '<other>' line (default: 1.0)",
    )
    return parser


def main() -> None:
    """Parse arguments, generate the report, and print it (or a clean error)."""
    parser = _build_parser()
    args = parser.parse_args()

    directory: Path = args.PATH
    min_percent: float = args.min_percent

    try:
        results = generate_size_report(directory, min_percent)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    print(results, end="")
```

- [ ] **Step 4: Add `src/dsz/__main__.py`**

```python
"""python -m dsz entry point."""

from dsz.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_cli.py tests/test_cli_subprocess.py -v`
Expected: PASS (all cases).

- [ ] **Step 6: Commit**

```bash
git add src/dsz/cli.py src/dsz/__main__.py tests/test_cli.py tests/test_cli_subprocess.py
git commit -m "fix: validate --min-percent range, broaden CLI error handling, add __main__"
```

---

## Task 7: Add CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `justfile` targets from Task 1 (`format`, `lint`, `typecheck`, `test` map to the same underlying `uv run ...` commands used directly here).
- Produces: a GitHub Actions workflow that runs on every push/PR to `main`.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v6

      - uses: astral-sh/setup-uv@v8.1.0
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync

      - name: Format check
        run: uv run ruff format --check src/ tests/

      - name: Lint
        run: uv run ruff check src/ tests/

      - name: Type check
        if: matrix.python-version == '3.13'
        run: uv run ty check src/

      - name: Test
        run: uv run pytest
```

(`actions/checkout@v6` and `astral-sh/setup-uv@v8.1.0` match the versions already pinned in this repo's `pypi.yml`/`testpypi.yml`, for consistency.)

- [ ] **Step 2: Validate the YAML is well-formed**

`pyyaml` isn't a project dependency, so don't reach for a Python one-liner here. Instead, diff the new file's structure against the two workflows already proven to work in this repo:

Run: `diff <(grep -oE '^ *' .github/workflows/pypi.yml | sort -u) <(grep -oE '^ *' .github/workflows/ci.yml | sort -u)`
Expected: no wildly different indentation levels (both files should use 2-space nesting throughout). Also visually confirm every `- name:`/`- uses:`/`run:` block in the new file lines up the same way it does in `pypi.yml`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add format/lint/typecheck/test workflow across Python 3.11-3.14"
```

---

## Task 8: Add `CLAUDE.md`

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: guidance for future Claude Code sessions working in this repo.

- [ ] **Step 1: Create `CLAUDE.md`**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`dsz` is a small Python CLI tool that shows disk usage of a directory's immediate children, sorted by size, as a bar chart. Python 3.11+, src layout, managed with `uv`.

## Commands

- **Install deps:** `uv sync`
- **Run tests:** `uv run pytest`
- **Run single test:** `uv run pytest tests/test_core.py::test_name -v`
- **Test with coverage:** `uv run pytest --cov=dsz`
- **Lint:** `uv run ruff check src/ tests/`
- **Format:** `uv run ruff format src/ tests/`
- **Type check:** `uv run ty check src/`
- **Everything:** `just` (runs format + lint + typecheck + test)

## Architecture

The project uses a `src/dsz/` layout with this module structure:

- `core.py` -- All scanning and formatting logic:
  - `_fmt_size()` -- byte count to human-readable string (B/KB/MB/GB/TB/PB).
  - `_leaf_size()` -- one non-directory entry's byte size; tolerant of races
    (entry vanishes between listing and stat) and non-regular-file types
    (FIFOs, sockets), both of which contribute 0 rather than raising.
  - `_dir_size()` -- iterative (stack-based, not recursive) total size of a
    directory tree. Uses the same race/permission tolerance as `_leaf_size`.
  - `_child_size()` -- dispatches an immediate child to `_dir_size` (directory)
    or `_leaf_size` (everything else).
  - `generate_size_report()` -- scans a path's immediate children concurrently
    (`ThreadPoolExecutor`, since scanning is I/O-bound) and renders the report.
- `cli.py` -- `argparse`-based entry point (`main()`), plus `_percent()` (validates
  `--min-percent` is a finite value in [0, 100]).
- `__main__.py` -- `python -m dsz` alias for the CLI.
- `__init__.py` -- package docstring (no public API is re-exported; this is a
  CLI tool, not a library).

Key design decisions:
- **Every filesystem operation that can race (a file/directory deleted or
  made unreadable between being listed and being examined) is tolerated,
  not raised.** A raced-out entry contributes 0 bytes and is still listed --
  it's never silently dropped, and it never crashes the scan. This is the
  single most important invariant in `core.py`; if you touch scanning logic,
  preserve it (see `tests/test_core.py::TestGenerateSizeReport::test_does_not_lose_siblings_after_one_entry_errors`
  for the regression this guards).
- **Hidden entries (leading dot) and symlinks are excluded entirely** at
  every level, not just the scan root.
- **Non-regular-file entries (FIFOs, sockets, device files) are listed but
  always size 0** -- they don't have a meaningful disk-usage figure.

## Workflow

- Every feature, fix, or other change gets its own branch and pull request --
  no direct commits to main.
- Commits must be atomic: one logical change per commit.
- Follow DRY -- extract shared logic rather than duplicating it. (The two
  directory-scanning implementations drifting out of sync was the root cause
  of several bugs fixed early in this project's history -- keep scanning
  logic in one place.)

## Code Style

- Google-style docstrings (enforced by ruff).
- Line length: 88 chars.
- All ruff rules enabled with pragmatic ignores (see `pyproject.toml`).
- Tests are exempt from docstring and type annotation rules.
- Prefer comments that explain *why*, not *what*.

## Testing Notes

- Tests use real filesystem operations via pytest's `tmp_path`, not mocks,
  wherever practical -- this is a filesystem tool, and the real syscalls are
  what actually need to behave correctly.
- Race conditions (entry deleted between listing and stat) are tested
  deterministically: create the entry, list it via `os.scandir`, delete it,
  *then* call the sizing function -- no timing or threading needed to
  reproduce the race.
- `monkeypatch.setattr(core.os, "scandir", ...)` is used to simulate a
  directory itself vanishing or becoming unreadable mid-scan.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md"
```

---

## Task 9: Final verification, README touch-ups, and cleanup

**Files:**
- Modify: `README.md`
- Verify: entire repository

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: a fully green `just all` run.

- [ ] **Step 1: Update `README.md`**

Add a note about the `--min-percent` valid range. Find this line in `README.md`:

```markdown
- `--min-percent N` — collapse entries below N% of the total into a single `<other>` line (default: 1.0)
```

Replace it with:

```markdown
- `--min-percent N` — collapse entries below N% of the total into a single `<other>` line (default: 1.0; N must be between 0 and 100)
```

- [ ] **Step 2: Run the full check suite**

Run: `cd /Users/kyle/code/dsz && just all`
Expected: `format`, `lint`, `typecheck`, and `test` all exit 0.

If `ruff check` surfaces violations not already covered by an ignore in `pyproject.toml`'s `[tool.ruff.lint] ignore` list (this is expected — the exact rule set wasn't hand-verified while writing this plan): fix the underlying code where the violation is real, or add a narrowly-scoped ignore (a `# noqa: RULE123` on the specific line, or — only if the rule is a poor fit for this codebase everywhere — add it to the shared `ignore` list with a one-line comment explaining why, matching the existing entries' style). Do not blanket-disable a rule to silence a single genuine finding.

If `ty check` surfaces type errors: fix them directly — the codebase is small enough that every type error should be resolvable without an ignore.

- [ ] **Step 3: Run coverage and sanity-check it**

Run: `just cov`
Expected: a coverage report with `core.py` and `cli.py` both showing high coverage (no hard percentage gate per this project's scope, but investigate any large gap — e.g., an entire branch with zero coverage usually means a missed test case, not an acceptable gap).

- [ ] **Step 4: Manually verify the CLI end-to-end**

Run: `uv run dsz .`
Expected: prints a real report for the repository's own working directory (header line with total size, followed by per-entry lines), with no traceback.

Run: `uv run dsz --min-percent 200`
Expected: prints an argparse usage error to stderr and exits 2 (out-of-range `--min-percent` is now rejected).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: note --min-percent's valid range in README"
```

---

## Self-Review Notes (for the plan author, not a task to execute)

- **Spec coverage:** all 15 review findings are addressed — #1/#2/#3 (unguarded stat/scandir races) in Tasks 3–4, #4 (cli exception handling) in Task 6, #5 (silent sibling-drop) in Task 4, #6 (FIFO/socket silent exclusion) in Task 4, #7/#8 (`_fmt_size` bugs) in Task 2, #9 (zero-byte hiding) in Task 4, #10 (`--min-percent nan`) in Task 6, #11 (duplicated scan logic) resolved by the Task 3/4 consolidation, #12 (bar/percent redundancy) in Task 4, #13 (O(N²) string concat) in Task 4 (list + join), #14 (sequential scanning) in Task 5, #15 (`requires-python` floor) in Task 1. Quality-parity items (tests, `ty`, `ruff`, `justfile`, pre-commit, CI, `CLAUDE.md`, `py.typed`) are in Tasks 1, 2–6 (tests alongside each fix), 7, and 8.
- **Sort-key idiom cleanup** (`lambda x: -x[-1]` → `key=..., reverse=True`) is folded into Task 4's rewrite rather than its own task, since it's a one-line part of the same function being rewritten there.
