from __future__ import annotations

import csv
import json
import sys
from decimal import Decimal

import questionary
import rich_click as click

from cli.constants.ui import ACCENT, PROMPT_STYLE
from cli.types.context import CliContext
from cli.types.enums import OutputFormat
from cli.types.labels import method_label, network_label
from cli.utils.console import err_console
from cli.utils.console import out_console as console
from cli.utils.cost_log import cost_log
from cli.utils.output import renderer


@click.group()
def mp() -> None:
    """machine payment tracking and cost management."""


@mp.group("cost", invoke_without_command=True)
@click.pass_context
def cost(ctx: click.Context) -> None:
    """view machine payment spend.

    \b
    without a subcommand, shows total spend summary.
    use 'list' to see itemized history or 'clear' to reset.
    """
    if ctx.invoked_subcommand is not None:
        return

    cli_ctx: CliContext = ctx.obj
    fmt = cli_ctx.output_format
    totals = cost_log.total()

    if not totals:
        err_console.print("\n  No machine payments recorded yet.\n")
        return

    if fmt == OutputFormat.JSON:
        out = {
            k: {"amount": str(v["amount"]), "calls": v["calls"]}
            for k, v in totals.items()
        }
        grand_amount = sum(v["amount"] for v in totals.values())
        grand_calls = sum(v["calls"] for v in totals.values())
        out["total"] = {"amount": str(grand_amount), "calls": grand_calls}
        console.print_json(json.dumps(out, default=str))
        return

    if fmt == OutputFormat.CSV:
        writer = csv.writer(sys.stdout)
        writer.writerow(["method", "network", "amount", "calls"])
        grand_amount = Decimal("0")
        grand_calls = 0
        for key, vals in totals.items():
            method, network = key.split(":", 1)
            writer.writerow([method, network, str(vals["amount"]), vals["calls"]])
            grand_amount += vals["amount"]
            grand_calls += vals["calls"]
        writer.writerow(["total", "all", str(grand_amount), grand_calls])
        return

    console.print("\n  [bold]Machine Payment Spend[/bold]\n")
    grand_amount = Decimal("0")
    grand_calls = 0
    for key, vals in totals.items():
        method, network = key.split(":", 1)
        m_label = method_label(method)
        n_label = network_label(network)
        amt = vals["amount"]
        calls = vals["calls"]
        console.print(f"  {m_label:<8} {n_label:<20} {amt:>12} USDC  ({calls} calls)")
        grand_amount += vals["amount"]
        grand_calls += vals["calls"]

    console.print(f"  {'':28} {'─' * 12}")
    console.print(f"  {'Total':<28} {grand_amount:>12} USDC  ({grand_calls} calls)")
    console.print()


@cost.command("list")
@click.pass_context
def cost_list(ctx: click.Context) -> None:
    """show full itemized payment history."""
    cli_ctx: CliContext = ctx.obj
    fmt = cli_ctx.output_format
    rows = cost_log.read()

    if not rows:
        err_console.print("\n  No machine payments recorded yet.\n")
        return

    if fmt in (OutputFormat.JSON, OutputFormat.CSV):
        renderer.render(rows, fmt)
        return

    from rich import box
    from rich.table import Table

    table = Table(box=box.ROUNDED, caption=f"Showing {len(rows)} payments")
    table.add_column("Timestamp")
    table.add_column("Method")
    table.add_column("Endpoint")
    table.add_column("Network")
    table.add_column("Amount", justify="right")
    table.add_column("Status", justify="right")

    for row in rows:
        table.add_row(
            row.get("timestamp", ""),
            method_label(row.get("method", "")),
            row.get("endpoint", ""),
            network_label(row.get("network", "")),
            row.get("amount", ""),
            row.get("http_status", ""),
        )

    console.print(table)

    totals = cost_log.total()
    if totals:
        parts = []
        for key, vals in totals.items():
            method, network = key.split(":", 1)
            parts.append(
                f"{vals['amount']} ({method_label(method)} {network_label(network)})"
            )
        console.print(f"\n  Total: {', '.join(parts)}\n")


@cost.command("clear")
@click.option(
    "--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt."
)
def cost_clear(yes: bool) -> None:
    """delete the cost log after confirmation."""
    if not yes:
        confirm = questionary.confirm(
            "Delete all payment history?",
            default=False,
            style=PROMPT_STYLE,
            qmark="●",
        ).ask()
        if confirm is None:
            raise click.Abort()
        if not confirm:
            err_console.print("\n  Cancelled.\n")
            return
    if cost_log.clear():
        err_console.print(f"\n  [{ACCENT}]✓ Cost log cleared.[/{ACCENT}]\n")
    else:
        err_console.print("\n  No cost log to clear.\n")
