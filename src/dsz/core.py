"""dsz scan module."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
    # no branch: the loop can never run to exhaustion -- the last iteration's
    # `unit == _UNITS[-1]` always breaks -- so its exhaustion arc is dead code
    # that no test can reach.
    for unit in _UNITS:  # pragma: no branch
        size /= 1024
        # Compare the *rounded* value against 1024, not the raw value --
        # otherwise a size that rounds up to "1024.0 KB" at display time
        # (e.g. 1048575 bytes) would stop one unit too early.
        if round(size, 1) < 1024 or unit == _UNITS[-1]:
            break

    return f"{size:.1f} {unit}"


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
        stat = entry.stat(follow_symlinks=False)
    except OSError:
        return 0
    return stat.st_size if entry.is_file(follow_symlinks=False) else 0


def _format_row(name: str, size: int, percent: float) -> str:
    """Format one report line: size, percent, name, and a proportional bar."""
    bar = "#" * round(percent / 5)
    return f"{_fmt_size(size):>10} {percent:>3.0f}% {name:<20} {bar}"


def _dir_size(path: str) -> int:
    """Return the total byte size of all files under path.

    Args:
        path: Directory to scan, recursively.

    Returns:
        The sum of every regular file's size under path. Symlinks are
        skipped. Directories that can't be listed (permission denied,
        removed mid-scan) contribute 0 rather than raising, so one
        unreadable subtree doesn't abort the rest of the scan. An entry
        whose `is_symlink()`/`is_dir()` check itself raises `OSError` (seen
        on filesystems that don't expose `d_type` from `readdir()`) is
        skipped without affecting its siblings.
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
                try:
                    is_symlink = entry.is_symlink()
                    is_dir = not is_symlink and entry.is_dir(follow_symlinks=False)
                except OSError:
                    # is_symlink()/is_dir() can raise on filesystems that
                    # don't expose d_type from readdir() (NFS, FAT, some
                    # FUSE mounts) -- skip just this entry, keep its siblings.
                    continue
                if is_symlink:
                    continue
                if is_dir:
                    stack.append(entry.path)
                else:
                    total_size += _leaf_size(entry)

    return total_size


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


def _list_children(path: Path) -> list[os.DirEntry[str]]:
    """List path's non-hidden, non-symlink immediate children.

    Args:
        path: Directory to list.

    Returns:
        Every entry whose name doesn't start with "." and that isn't a
        symlink. An entry whose `is_symlink()` check itself raises
        `OSError` (seen on filesystems that don't expose `d_type` from
        `readdir()`) is skipped without affecting its siblings. An empty
        list is returned if `path` itself can't be listed (permission
        denied, removed mid-scan) rather than raising -- that's a race,
        not a usage error, since the caller already confirmed `path`
        exists and is a directory.
    """
    children: list[os.DirEntry[str]] = []
    try:
        with os.scandir(path) as dir_iter:
            for entry in dir_iter:
                if entry.name.startswith("."):
                    continue
                try:
                    if entry.is_symlink():
                        continue
                except OSError:
                    continue
                children.append(entry)
    except OSError:
        return []
    return children


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

    children = _list_children(path)

    with ThreadPoolExecutor() as pool:
        sizes = list(pool.map(_child_size, children))

    entries = dict(zip((c.name for c in children), sizes, strict=True))
    total_size = sum(sizes)

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
        out_lines.append(_format_row(name, size, percent))

    if below:
        other_size = sum(size for _, size, _ in below)
        other_percent = (other_size / total_size * 100) if total_size else 0.0
        other_label = f"<other {len(below)}>"
        out_lines.append(_format_row(other_label, other_size, other_percent))

    return "\n".join(out_lines) + "\n"
