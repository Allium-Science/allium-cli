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
from cli.types.profiles import ApiKeyProfile
from cli.utils.async_cmd import async_command
from cli.utils.console import err_console as console
from cli.utils.errors import (
    format_api_error,
    output_response,
    resolve_client,
    resolve_profile,
)
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
      run-sql       execute ad-hoc SQL (x402/Tempo auth required)
      create-query  create a saved Explorer query (api-key path)
      run           execute a saved query by ID
      status        check a query run's status
      results       fetch results of a completed run
      schemas       browse and search Allium's table schemas
      docs          browse and search Allium's documentation
    """


@explorer.command("create-query")
@click.argument("sql_or_file", required=False)
@click.option(
    "--title",
    default=None,
    help=(
        "Title for the saved query. Defaults to 'allium-cli passthrough' "
        "when --passthrough is set, 'Created via allium-cli' otherwise."
    ),
)
@click.option(
    "--limit",
    default=10000,
    type=click.IntRange(1, 100000),
    help="Default row limit for runs of this query (default: 10000).",
)
@click.option(
    "--passthrough",
    is_flag=True,
    default=False,
    help=(
        "Shortcut: create a query whose SQL is `{{ sql_query }}`. "
        'Run any SQL through it via `--param sql_query="..."`.'
    ),
)
@click.pass_context
@async_command
async def create_query(
    ctx: click.Context,
    sql_or_file: str | None,
    title: str | None,
    limit: int,
    passthrough: bool,
) -> None:
    """create a saved Explorer query.

    \b
    SQL_OR_FILE accepts an inline SQL string, a path to a .sql file, or '-'
    to read from stdin. Required unless --passthrough is set. Use Jinja
    `{{ name }}` placeholders for parameters.

    Returns the new query_id; run it later with `allium explorer run <ID>`.

    \b
    examples:
      # Passthrough query for ad-hoc SQL with an api-key profile:
      allium explorer create-query --passthrough
      # → {"query_id": "..."}
      allium explorer run <ID> --param sql_query="SELECT ..."

      # Parameterized query:
      allium explorer create-query \\
        --title "Recent ethereum blocks" \\
        "SELECT block_number FROM ethereum.raw.blocks \\
         WHERE block_timestamp > '{{ since }}' LIMIT {{ n }}"

    Requires an api_key profile (x402 / Tempo cannot create saved queries).
    """
    profile = resolve_profile(ctx)
    if not isinstance(profile, ApiKeyProfile):
        raise click.UsageError(
            "`create-query` requires an api_key profile — your active profile "
            "is x402 / Tempo. Switch with `allium auth use <api_key_profile>`."
        )

    if passthrough:
        sql = "{{ sql_query }}"
        if title is None:
            title = "allium-cli passthrough"
    else:
        if not sql_or_file:
            raise click.UsageError(
                "Pass SQL_OR_FILE (inline string, .sql file, or '-' for stdin)"
                " — or use --passthrough to create an ad-hoc-SQL passthrough"
                " query."
            )
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
            raise click.UsageError("SQL is empty.")
        if title is None:
            title = "Created via allium-cli"

    client = resolve_client(ctx)
    body: dict[str, Any] = {
        "title": title,
        "config": {"sql": sql, "limit": limit},
    }
    resp = await client.post("/api/v1/explorer/queries", json=body)
    output_response(ctx, resp)


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

    \b
    using an API key? You cannot run ad-hoc SQL directly. Two-step instead:
      1. allium explorer create-query --passthrough
         # → returns a query_id
      2. allium explorer run <QUERY_ID> --param sql_query="SELECT ..."
    Or switch to an x402 / Tempo profile: `allium auth use <name>`.
    """
    profile = resolve_profile(ctx)
    if isinstance(profile, ApiKeyProfile):
        raise click.UsageError(
            "Ad-hoc `run-sql` requires x402 or Tempo auth — "
            "your active profile is an API key.\n"
            "API-key path: create a passthrough saved query, then run it.\n"
            "  1. allium explorer create-query --passthrough\n"
            "     # → returns a query_id\n"
            "  2. allium explorer run <QUERY_ID>"
            ' --param sql_query="<your SQL>"\n'
            "Or switch profiles: `allium auth use <x402_or_tempo_profile>`."
        )
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

    # `parameters` is required by the server (422 when missing) even when empty.
    body: dict[str, Any] = {"parameters": parameters}

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


# schemas


@explorer.group()
@click.pass_context
def schemas(ctx: click.Context) -> None:
    """browse and search Allium's table schemas (catalogs, schemas, tables)."""


@schemas.command("browse")
@click.argument("path", required=False, default="")
@click.pass_context
@async_command
async def schemas_browse(ctx: click.Context, path: str) -> None:
    """browse Allium's data schema hierarchy like a filesystem.

    \b
    run with no PATH to list every catalog you can access. drill in with
    dot-separated paths:
      allium explorer schemas browse                  # list catalogs
      allium explorer schemas browse ethereum         # list schemas
      allium explorer schemas browse ethereum.raw     # list tables
      allium explorer schemas browse ethereum.raw.blocks  # full table details
    """
    client = resolve_client(ctx)
    resp = await client.get("/api/v1/docs/schemas/browse", params={"path": path})
    output_response(ctx, resp)


@schemas.command("search")
@click.argument("query")
@click.pass_context
@async_command
async def schemas_search(ctx: click.Context, query: str) -> None:
    """semantic search across Allium's table schemas.

    returns a list of matching table IDs (full names, e.g. `ethereum.raw.blocks`).
    feed any result back into `schemas browse <id>` for the full column metadata.
    """
    client = resolve_client(ctx)
    resp = await client.get("/api/v1/docs/schemas/search", params={"query": query})
    output_response(ctx, resp)


# docs


@explorer.group()
@click.pass_context
def docs(ctx: click.Context) -> None:
    """browse and search Allium's documentation."""


@docs.command("browse")
@click.argument("path", required=False, default="")
@click.pass_context
@async_command
async def docs_browse(ctx: click.Context, path: str) -> None:
    """browse Allium's documentation hierarchy like a filesystem.

    \b
    run with no PATH to list root directories. drill in with paths like:
      allium explorer docs browse                       # list root
      allium explorer docs browse api                   # list api/ contents
      allium explorer docs browse api/overview.mdx      # get file content
    """
    client = resolve_client(ctx)
    resp = await client.get("/api/v1/docs/docs/browse", params={"path": path})
    output_response(ctx, resp)


@docs.command("search")
@click.argument("query")
@click.option(
    "--page-size",
    default=10,
    type=click.IntRange(1, 50),
    help="Number of results to return (1-50, default 10).",
)
@click.pass_context
@async_command
async def docs_search(ctx: click.Context, query: str, page_size: int) -> None:
    """semantic search across Allium's documentation.

    returns matching doc snippets with content, path, and relevance metadata.
    pair with `docs browse <path>` to retrieve the full file for a hit.
    """
    client = resolve_client(ctx)
    resp = await client.get(
        "/api/v1/docs/docs/search",
        params={"query": query, "page_size": page_size},
    )
    output_response(ctx, resp)
