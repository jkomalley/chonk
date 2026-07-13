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
