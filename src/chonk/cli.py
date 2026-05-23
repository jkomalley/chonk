"""chonk cli module."""

from pathlib import Path

import argparse


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
        metavar="N",
        type=float,
        help="collapse entries below N%% into one line",
    )
    args = parser.parse_args()

    directory: Path = args.PATH
    min_percent: float = args.min_percent

    # Placeholder for actual directory size analysis logic
    print(f"DIRECTORY: {directory.absolute()}")
    print(f"MIN_PERCENT: {min_percent}")
