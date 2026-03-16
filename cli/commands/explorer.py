from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

import rich_click as click
from rich.live import Live
from rich.spinner import Spinner

from cli.clients.protocol import ClientProtocol
from cli.constants.config import EXIT_ERROR
from cli.constants.ui import ACCENT
from cli.types.context import CliContext
from cli.utils.async_cmd import async_command
from cli.utils.console import err_console as console
from cli.utils.errors import format_api_error, output_response, resolve_client
from cli.utils.output import renderer

TERMINAL_STATUSES = {"success", "failed", "canceled"}
INITIAL_POLL_INTERVAL = 2.0
MAX_POLL_INTERVAL = 15.0
MAX_POLL_TIME = 600.0


async def _poll_until_done(
    ctx: click.Context, client: ClientProtocol, run_id: str
) -> str:
    """poll query run status with exponential backoff."""
    cli_ctx: CliContext = ctx.obj
    verbose = cli_ctx.verbose
    start = asyncio.get_event_loop().time()
    status = "created"
    interval = INITIAL_POLL_INTERVAL

    live_ctx: contextlib.AbstractContextManager[Any] = (
        Live(
            Spinner("dots", text=f"  Query run {run_id}: [bold]{status}[/bold]"),
            console=console,
            transient=True,
        )
        if verbose
        else contextlib.nullcontext()
    )

    with live_ctx as live:
        while True:
            resp = await client.get(f"/api/v1/explorer/query-runs/{run_id}/status")
            if resp.status_code >= 400:
                msg = format_api_error(resp)
                console.print(f"[red]Error ({resp.status_code}):[/red] {msg}")
                sys.exit(EXIT_ERROR)

            data = resp.json()
            status = data.get("status", status) if isinstance(data, dict) else str(data)

            if verbose and live is not None:
                live.update(
                    Spinner(
                        "dots",
                        text=f"  Query run {run_id}: [bold]{status}[/bold]",
                    )
                )

            if status in TERMINAL_STATUSES:
                break

            elapsed = asyncio.get_event_loop().time() - start
            if elapsed > MAX_POLL_TIME:
                console.print(
                    f"[yellow]Polling timed out after {MAX_POLL_TIME:.0f}s. "
                    f"Check status with: allium explorer status {run_id}[/yellow]"
                )
                return status

            await asyncio.sleep(interval)
            interval = min(interval * 1.5, MAX_POLL_INTERVAL)

    if verbose:
        if status == "success":
            console.print(f"[{ACCENT}]Query run {run_id} completed.[/{ACCENT}]")
        elif status == "canceled":
            console.print(f"[yellow]Query run {run_id} was canceled.[/yellow]")

    if status == "failed":
        console.print(f"[red]Query run {run_id} failed.[/red]")
        await _show_error(client, run_id)

    return status


async def _show_error(client: ClientProtocol, run_id: str) -> None:
    resp = await client.get(f"/api/v1/explorer/query-runs/{run_id}/error")
    if resp.status_code == 200:
        try:
            error_data = resp.json()
            if error_data:
                console.print(f"[red]Error: {error_data}[/red]")
        except (ValueError, KeyError):
            if resp.text:
                console.print(f"[red]Error: {resp.text}[/red]")


async def _fetch_and_display_results(
    ctx: click.Context, client: ClientProtocol, run_id: str
) -> None:
    cli_ctx: CliContext = ctx.obj
    fmt = cli_ctx.output_format
    result_format = "csv" if fmt == "csv" else "json"
    resp = await client.get(
        f"/api/v1/explorer/query-runs/{run_id}/results",
        params={"f": result_format},
    )

    if fmt == "csv" and resp.status_code == 200:
        click.echo(resp.text)
        return

    output_response(ctx, resp)


async def _run_async_and_poll(
    ctx: click.Context,
    client: ClientProtocol,
    endpoint: str,
    body: dict[str, Any],
    no_wait: bool,
) -> None:
    """submit async query, optionally poll and fetch results."""
    cli_ctx: CliContext = ctx.obj
    verbose = cli_ctx.verbose
    resp = await client.post(endpoint, json=body)

    if resp.status_code >= 400:
        output_response(ctx, resp)
        return

    data = resp.json()
    run_id = data.get("run_id", "")
    if not run_id:
        console.print("[red]No run_id in response.[/red]")
        console.print_json(json.dumps(data, default=str))
        sys.exit(EXIT_ERROR)

    if no_wait:
        renderer.render({"run_id": run_id}, cli_ctx.output_format)
        return

    if verbose:
        console.print(f"Run ID: [bold]{run_id}[/bold]")

    status = await _poll_until_done(ctx, client, run_id)

    if status == "success":
        await _fetch_and_display_results(ctx, client, run_id)


@click.group()
@click.pass_context
def explorer(ctx: click.Context) -> None:
    """run SQL queries on Allium's data warehouse.

    \b
    available subcommands:
      run-sql   execute ad-hoc SQL (x402/Tempo auth required)
      run       execute a saved query by ID
      status    check a query run's status
      results   fetch results of a completed run
    """


@explorer.command("run-sql")
@click.argument("sql_or_file")
@click.option("--limit", default=None, type=int, help="Row limit for the query.")
@click.option(
    "--no-wait",
    is_flag=True,
    default=False,
    help="Print the run_id immediately and exit without polling.",
)
@click.pass_context
@async_command
async def run_sql(
    ctx: click.Context,
    sql_or_file: str,
    limit: int | None,
    no_wait: bool,
) -> None:
    """execute ad-hoc SQL against Allium's warehouse.

    requires x402 or Tempo auth (not API key). SQL_OR_FILE accepts an inline
    SQL string, a path to a .sql file, or '-' to read from stdin.
    """
    client = resolve_client(ctx)

    if sql_or_file == "-":
        sql = sys.stdin.read().strip()
    else:
        path = Path(sql_or_file)
        if path.suffix == ".sql":
            if not path.exists():
                raise click.UsageError(f"File not found: {path}")
            sql = path.read_text().strip()
        else:
            sql = sql_or_file

    if not sql:
        raise click.UsageError("SQL query is empty.")

    body: dict[str, Any] = {"parameters": {"sql": sql}}
    if limit is not None:
        body["run_config"] = {"limit": limit}

    await _run_async_and_poll(
        ctx, client, "/api/v1/explorer/queries/run-async", body, no_wait
    )


@explorer.command("run")
@click.argument("query_id")
@click.option(
    "--param", multiple=True, help="Query parameter as key=value (repeatable)."
)
@click.option("--limit", default=None, type=int, help="Row limit for the query.")
@click.option("--compute-profile", default=None, help="Compute profile, e.g. 'large'.")
@click.option(
    "--no-wait",
    is_flag=True,
    default=False,
    help="Print the run_id immediately and exit without polling.",
)
@click.pass_context
@async_command
async def run_query(
    ctx: click.Context,
    query_id: str,
    param: tuple[str, ...],
    limit: int | None,
    compute_profile: str | None,
    no_wait: bool,
) -> None:
    """execute a saved Explorer query by its ID.

    create queries at app.allium.so or via the API. parameters are passed as
    repeatable --param flags: --param key=value
    """
    client = resolve_client(ctx)

    parameters: dict[str, str] = {}
    for p in param:
        if "=" not in p:
            raise click.UsageError(f"Invalid --param format: '{p}'. Use key=value.")
        k, v = p.split("=", 1)
        parameters[k] = v

    body: dict[str, Any] = {}
    if parameters:
        body["parameters"] = parameters

    run_config: dict[str, Any] = {}
    if limit is not None:
        run_config["limit"] = limit
    if compute_profile:
        run_config["compute_profile"] = compute_profile
    if run_config:
        body["run_config"] = run_config

    await _run_async_and_poll(
        ctx,
        client,
        f"/api/v1/explorer/queries/{query_id}/run-async",
        body,
        no_wait,
    )


@explorer.command("status")
@click.argument("run_id")
@click.pass_context
@async_command
async def status(ctx: click.Context, run_id: str) -> None:
    """check the current status of a query run.

    possible statuses: created, running, success, failed, canceled.
    """
    client = resolve_client(ctx)
    resp = await client.get(f"/api/v1/explorer/query-runs/{run_id}/status")
    output_response(ctx, resp)


@explorer.command("results")
@click.argument("run_id")
@click.pass_context
@async_command
async def results(ctx: click.Context, run_id: str) -> None:
    """download results of a completed query run.

    output format follows the global --format flag.
    """
    client = resolve_client(ctx)
    await _fetch_and_display_results(ctx, client, run_id)
