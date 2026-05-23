"""chonk cli module."""

from chonk.core import generate_size_report

from pathlib import Path

import argparse
import sys


def main() -> None:
    """Main entry point for the chonk CLI."""
    parser = argparse.ArgumentParser(description="Directory size viewer.")
    parser.add_argument(
        "PATH",
        nargs="?",
        default=".",
        type=Path,
        help="directory to scan. Defaults to current directory.",
    )
    parser.add_argument(
        "--min-percent",
        default=1.0,
        metavar="N",
        type=float,
        help="collapse entries below N%% into one line",
    )
    args = parser.parse_args()

    directory: Path = args.PATH
    min_percent: float = args.min_percent

    try:
        results = generate_size_report(directory, min_percent)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)

    print(results, end="")
