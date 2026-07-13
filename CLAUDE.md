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
  for the regression this guards). The one deliberate exception: a top-level
  entry whose `is_symlink()` check itself raises `OSError` is dropped from
  the listing rather than sized as 0, since its symlink-ness (and therefore
  whether it should be excluded) can't be determined -- see
  `test_does_not_lose_siblings_after_one_entry_is_symlink_errors`.
- **Symlinks are excluded entirely at every level.** Hidden entries
  (leading dot) are excluded only from the top-level listing (both from
  display and from the total) -- a subdirectory's own hidden files are
  still counted toward its total, matching `du`-like behavior.
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
- Every release gets a `CHANGELOG.md` entry (Keep a Changelog format) added
  in the same PR as the version bump in `pyproject.toml`. After publishing,
  create the GitHub release with `gh release create vX.Y.Z --generate-notes`.

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
