from chonk.core import generate_size_report

from pathlib import Path

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Show disk usage of a directory's immediate children.")
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
        type=float,
        help="collapse entries below N%% of total into one '<other>' line (default: 1.0)",
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
