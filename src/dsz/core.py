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


def _dir_size(path: str) -> int:
    """Return total byte size of all files under path, skipping symlinks and permission-denied entries."""
    total_size = 0
    stack = [path]

    while stack:
        current = stack.pop()

        try:
            scandir_ctx = os.scandir(current)
        except PermissionError:
            continue

        with scandir_ctx as dir_iter:
            for entry in dir_iter:
                if entry.is_symlink():
                    continue
                try:
                    entry_stat = entry.stat()
                except OSError:
                    continue
                if entry.is_file(follow_symlinks=False):
                    total_size += entry_stat.st_size
                elif entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)

    return total_size


def generate_size_report(path: Path, min_percent: float) -> str:
    """Scan path's immediate children and return a formatted size report string.

    Raises ValueError if path does not exist or is not a directory.
    Hidden entries (leading dot) and symlinks are excluded from all counts.
    Entries below min_percent of the total are collapsed into a single '<other N>' line.
    """
    if not path.exists():
        msg = f"path '{path}' does not exist"
        raise ValueError(msg)

    if not path.is_dir():
        msg = f"path '{path}' is not a directory"
        raise ValueError(msg)

    total_size: int = 0

    entries: dict[str, int] = {}

    try:
        with os.scandir(path) as dir_iter:
            for entry in dir_iter:
                if entry.name.startswith("."):
                    continue
                if entry.is_symlink():
                    continue
                entry_stat = entry.stat()
                if entry.is_file(follow_symlinks=False):
                    total_size += entry_stat.st_size
                    entries[entry.name] = entry_stat.st_size
                elif entry.is_dir(follow_symlinks=False):
                    entry_size = _dir_size(entry.path)
                    total_size += entry_size
                    entries[entry.name] = entry_size
    except PermissionError:
        pass  # unreadable directory: return header with whatever was counted

    out = f"{path.absolute()}    {_fmt_size(total_size)}\n"

    if not entries or total_size == 0:
        return out

    sorted_entries = sorted(entries.items(), key=lambda x: -x[-1])

    above, below = [], []

    for name, size in sorted_entries:
        percent = (size / total_size) * 100
        (above if percent >= min_percent else below).append((name, size, percent))

    for entry, size, percent in above:
        bar = "#" * round(size / total_size * 20)
        out += f"{_fmt_size(size):>10} {percent:>3.0f}% {entry:<20} {bar}\n"

    if below:
        other_size = sum(size for _, size, _ in below)
        other_percent = (other_size / total_size) * 100
        other_count = len(below)
        bar = "#" * round(other_size / total_size * 20)
        out += f"{_fmt_size(other_size):>10} {other_percent:>3.0f}% {f'<other {other_count}>':<20} {bar}\n"

    return out
