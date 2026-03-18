from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from cli.main import _hoist_global_options, cli
from cli.types.context import CliContext


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

    def test_hoist_quiet_short(self):
        result = _hoist_global_options(["realtime", "prices", "-q"])
        assert result == ["-q", "realtime", "prices"]

    def test_hoist_quiet_long(self):
        result = _hoist_global_options(["realtime", "--quiet", "prices"])
        assert result == ["--quiet", "realtime", "prices"]

    def test_hoist_quiet_and_verbose(self):
        result = _hoist_global_options(["realtime", "-q", "-v"])
        assert result == ["-q", "-v", "realtime"]

    def test_hoist_quiet_with_profile(self):
        result = _hoist_global_options(
            ["explorer", "run", "--quiet", "--profile", "dev"]
        )
        assert result == ["--quiet", "--profile", "dev", "explorer", "run"]


class TestQuietFlag:
    """--quiet / -q sets quiet=True on CliContext."""

    @staticmethod
    def _invoke_cli(args: list[str]) -> CliContext:
        """Invoke cli group and return the CliContext stored in ctx.obj."""
        import click as _click

        captured: dict = {}

        @cli.command("_test_noop")
        @_click.pass_context
        def _noop(ctx: _click.Context) -> None:
            captured["obj"] = ctx.obj

        try:
            runner = CliRunner()
            result = runner.invoke(cli, args + ["_test_noop"])
            assert result.exit_code == 0, result.output
            return captured["obj"]
        finally:
            cli.commands.pop("_test_noop", None)  # type: ignore[union-attr]

    def test_quiet_long_flag(self):
        ctx = self._invoke_cli(["--quiet"])
        assert isinstance(ctx, CliContext)
        assert ctx.quiet is True

    def test_quiet_short_flag(self):
        ctx = self._invoke_cli(["-q"])
        assert isinstance(ctx, CliContext)
        assert ctx.quiet is True

    def test_default_quiet_is_false(self):
        ctx = self._invoke_cli([])
        assert isinstance(ctx, CliContext)
        assert ctx.quiet is False


class TestMainQuietSuppressesUpdateCheck:
    """main() skips check_for_updates when -q/--quiet is in sys.argv."""

    @patch("cli.main.check_for_updates")
    @patch("cli.main.cli")
    def test_quiet_suppresses_update_check(self, mock_cli, mock_check):
        with patch("cli.main.sys") as mock_sys:
            mock_sys.argv = ["allium", "-q"]
            from cli.main import main

            main()
            mock_check.assert_not_called()

    @patch("cli.main.check_for_updates")
    @patch("cli.main.cli")
    def test_no_quiet_runs_update_check(self, mock_cli, mock_check):
        with patch("cli.main.sys") as mock_sys:
            mock_sys.argv = ["allium", "realtime"]
            from cli.main import main

            main()
            mock_check.assert_called_once()
