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
        help="collapse entries below N%% of total into '<other>' (default: 1.0)",
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
