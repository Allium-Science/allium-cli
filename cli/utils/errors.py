from __future__ import annotations

import json
import sys
from typing import Any

import rich_click as click

from cli.constants.config import EXIT_AUTH, EXIT_ERROR
from cli.types.context import CliContext
from cli.utils.console import err_console as console
from cli.utils.output import renderer


def format_api_error(response: Any) -> str:
    """extract a readable error message from an API response."""
    try:
        body = response.json()
    except (ValueError, KeyError):
        return response.text or f"HTTP {response.status_code}"

    if isinstance(body, dict):
        for key in ("message", "detail", "error"):
            if key in body and body[key]:
                val = body[key]
                if isinstance(val, str):
                    return val
                return json.dumps(val, default=str)

    return json.dumps(body, default=str)


def output_response(ctx: click.Context, response: Any) -> None:
    """check response status, render output or exit on error."""
    if response.status_code >= 400:
        msg = format_api_error(response)
        console.print(f"[red]Error ({response.status_code}):[/red] {msg}")
        sys.exit(EXIT_ERROR)

    data = response.json()
    cli_ctx: CliContext = ctx.obj
    renderer.render(data, cli_ctx.output_format)


def resolve_client(ctx: click.Context) -> Any:
    """get an authenticated client from the click context."""
    from cli.clients import get_client
    from cli.utils.config import config_manager

    cli_ctx: CliContext = ctx.obj
    profile_name = cli_ctx.profile_override
    if profile_name:
        profile = config_manager.get_profile(profile_name)
        if not profile:
            console.print(f"[red]Profile '{profile_name}' not found.[/red]")
            sys.exit(EXIT_AUTH)
    else:
        profile = config_manager.get_active_profile()
        if not profile:
            msg = "No active profile. Run [bold]allium auth setup[/bold] first."
            console.print(f"[red]{msg}[/red]")
            sys.exit(EXIT_AUTH)
    return get_client(profile)
