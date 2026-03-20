from __future__ import annotations

from click.testing import CliRunner

from cli.main import _hoist_global_options, cli


class TestHoistGlobalOptions:
    def test_moves_verbose_flag(self):
        args = ["explorer", "run-sql", "SELECT 1", "-v"]
        assert _hoist_global_options(args) == [
            "-v",
            "explorer",
            "run-sql",
            "SELECT 1",
        ]

    def test_moves_profile_option(self):
        args = ["realtime", "prices", "latest", "--profile", "myprofile"]
        result = _hoist_global_options(args)
        assert result[:2] == ["--profile", "myprofile"]
        assert "realtime" in result

    def test_moves_format_option(self):
        args = ["explorer", "run-sql", "SELECT 1", "--format", "csv"]
        result = _hoist_global_options(args)
        assert result[:2] == ["--format", "csv"]

    def test_moves_multiple_globals(self):
        args = ["explorer", "run-sql", "q.sql", "-v", "--format", "table"]
        result = _hoist_global_options(args)
        assert result[0] == "-v"
        assert result[1:3] == ["--format", "table"]
        assert "explorer" in result

    def test_no_globals_unchanged(self):
        args = ["auth", "list"]
        assert _hoist_global_options(args) == ["auth", "list"]

    def test_empty_args(self):
        assert _hoist_global_options([]) == []

    def test_global_already_at_front(self):
        args = ["-v", "explorer", "run-sql", "SELECT 1"]
        assert _hoist_global_options(args) == args

    def test_verbose_long_form(self):
        args = ["auth", "list", "--verbose"]
        result = _hoist_global_options(args)
        assert result[0] == "--verbose"


class TestVersionFlag:
    def test_version_flag_outputs_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "allium" in result.output.lower()

    def test_version_flag_contains_version_number(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Version output should contain a semver-like pattern
        assert "." in result.output
