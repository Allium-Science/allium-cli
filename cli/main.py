import sys

import rich_click as click

from cli.commands import register_commands
from cli.constants.ui import ACCENT, LOGO
from cli.types.context import CliContext
from cli.types.enums import OutputFormat
from cli.utils.version import check_for_updates

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.MAX_WIDTH = 120
click.rich_click.STYLE_ERRORS_SUGGESTION = "dim"
click.rich_click.ERRORS_SUGGESTION = (
    "Try running the '--help' flag for more information."
)
click.rich_click.STYLE_COMMANDS_PANEL_BORDER = ACCENT
click.rich_click.STYLE_OPTIONS_PANEL_BORDER = "dim"
click.rich_click.STYLE_COMMANDS_TABLE_LEADING = 1
click.rich_click.STYLE_COMMANDS_TABLE_PAD_EDGE = True
click.rich_click.COMMAND_GROUPS = {
    "allium": [
        {"name": "Data Queries", "commands": ["realtime", "explorer"]},
        {"name": "Configuration", "commands": ["auth", "mp"]},
    ],
    "allium realtime": [
        {"name": "General", "commands": ["supported-chains"]},
        {"name": "Market Data", "commands": ["prices", "tokens"]},
        {
            "name": "Wallet Data",
            "commands": [
                "balances",
                "holdings",
                "pnl",
                "pnl-by-token",
                "positions",
                "transactions",
            ],
        },
    ],
}

_GLOBAL_FLAGS = {"-v", "--verbose"}
_GLOBAL_OPTIONS = {"--profile", "--format"}


def _hoist_global_options(args: list[str]) -> list[str]:
    """move global flags/options to the front of the arg list."""
    front: list[str] = []
    rest: list[str] = []
    i = 0
    while i < len(args):
        if args[i] in _GLOBAL_FLAGS:
            front.append(args[i])
            i += 1
        elif args[i] in _GLOBAL_OPTIONS and i + 1 < len(args):
            front.extend([args[i], args[i + 1]])
            i += 2
        else:
            rest.append(args[i])
            i += 1
    return front + rest


_HELP = (
    "\b\n" + LOGO + "\n⠀\n⠀\n"
    "[bold]Get started:[/bold]\n"
    "  allium auth setup          Configure authentication\n"
    "  allium realtime --help     Realtime data (prices, wallets, tokens)\n"
    "  allium explorer --help     SQL queries on Allium Explorer\n"
    "  https://docs.allium.so     Full documentation"
)


@click.group(help=_HELP)
@click.version_option(
    version=None,
    package_name="allium-cli",
    prog_name="allium",
)
@click.option(
    "--profile",
    default=None,
    help="Auth profile to use (overrides active profile).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "table", "csv"]),
    default="json",
    help="Output format.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show progress details (run IDs, spinners, status messages).",
)
@click.pass_context
def cli(
    ctx: click.Context, profile: str | None, output_format: str, verbose: bool
) -> None:
    ctx.obj = CliContext(
        profile_override=profile,
        output_format=OutputFormat(output_format),
        verbose=verbose,
    )


register_commands(cli)


def main() -> None:
    """entry point; hoists global options then invokes click."""
    sys.argv[1:] = _hoist_global_options(sys.argv[1:])
    check_for_updates()
    cli()


if __name__ == "__main__":
    main()
