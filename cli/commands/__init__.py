from __future__ import annotations

import rich_click as click


def register_commands(cli: click.Group) -> None:
    """lazily import and attach all command groups."""
    from cli.commands.auth import auth
    from cli.commands.explorer import explorer
    from cli.commands.mp import mp
    from cli.commands.realtime import realtime

    cli.add_command(auth)
    cli.add_command(realtime)
    cli.add_command(explorer)
    cli.add_command(mp)
