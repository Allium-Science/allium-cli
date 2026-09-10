from __future__ import annotations

import csv
import json
import re
import sys
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

from cli.constants.config import EXIT_ERROR
from cli.types.enums import OutputFormat
from cli.utils.console import err_console, out_console


class OutputRenderer:
    """renders API response data in the requested format."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or out_console

    def render(self, data: Any, fmt: OutputFormat) -> None:
        if fmt == OutputFormat.JSON:
            self._json(data)
        elif fmt == OutputFormat.TABLE:
            self._table(data)
        elif fmt == OutputFormat.CSV:
            self._csv(data)
        else:
            self._json(data)

    def _json(self, data: Any) -> None:
        print(json.dumps(data, default=str, indent=2))

    def _table(self, data: Any) -> None:
        rows = _extract_rows(data)
        if not rows:
            self._console.print_json(json.dumps(data, default=str))
            return

        columns = list(rows[0].keys())
        numeric_cols = _detect_numeric_columns(rows, columns)

        is_tty = sys.stdout.isatty()

        if is_tty:
            table = Table(box=box.ROUNDED, caption=f"Showing {len(rows)} rows")
        else:
            table = Table(box=None, show_edge=False, pad_edge=False)

        for col in columns:
            justify = "right" if col in numeric_cols else "left"
            table.add_column(col, justify=justify)

        for row in rows:
            table.add_row(*(_format_cell(str(row.get(col, ""))) for col in columns))

        self._console.print(table)

        if not is_tty:
            err_console.print(f"Showing {len(rows)} rows")

    def _csv(self, data: Any) -> None:
        rows = _extract_rows(data)
        if not rows:
            err_console.print(
                "[red]Cannot render as CSV:[/red] response is not tabular data."
            )
            sys.exit(EXIT_ERROR)

        columns = list(rows[0].keys())
        writer = csv.DictWriter(sys.stdout, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(v) for k, v in row.items()})


def _extract_rows(data: Any) -> list[dict[str, Any]]:
    """try to extract a list of dicts from various response shapes."""
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data
        return []
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
    return []


_NUMERIC_RE = re.compile(r"^-?\d[\d,.]*(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def _detect_numeric_columns(rows: list[dict[str, Any]], columns: list[str]) -> set[str]:
    numeric: set[str] = set()
    for col in columns:
        values = [str(row.get(col, "")) for row in rows if row.get(col) is not None]
        if values and all(_NUMERIC_RE.match(v) for v in values):
            numeric.add(col)
    return numeric


def _format_cell(value: str) -> str:
    if len(value) > 30 and value.startswith("0x"):
        return f"{value[:10]}...{value[-6:]}"
    return value


renderer = OutputRenderer()
