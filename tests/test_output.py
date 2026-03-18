from __future__ import annotations

import io
import json
import sys
from unittest.mock import patch

from cli.types.enums import OutputFormat
from cli.utils.output import OutputRenderer, _flatten_rows


class TestFlattenRows:
    def test_nested_dicts_produce_dot_notation_keys(self):
        rows = [
            {"id": 1, "info": {"name": "Tether USD", "symbol": "USDT"}},
            {"id": 2, "info": {"name": "USD Coin", "symbol": "USDC"}},
        ]
        result = _flatten_rows(rows)
        assert result == [
            {"id": 1, "info.name": "Tether USD", "info.symbol": "USDT"},
            {"id": 2, "info.name": "USD Coin", "info.symbol": "USDC"},
        ]

    def test_lists_serialized_as_json(self):
        rows = [{"id": 1, "tags": ["stablecoin", "erc20"]}]
        result = _flatten_rows(rows)
        assert result == [{"id": 1, "tags": '["stablecoin", "erc20"]'}]
        # Verify it's valid JSON
        assert json.loads(result[0]["tags"]) == ["stablecoin", "erc20"]

    def test_flat_data_passes_through_unchanged(self):
        rows = [
            {"id": 1, "name": "Tether", "price": "1.00"},
            {"id": 2, "name": "Ethereum", "price": "3000.00"},
        ]
        result = _flatten_rows(rows)
        assert result == rows

    def test_empty_rows_returns_empty(self):
        assert _flatten_rows([]) == []

    def test_mixed_nested_and_flat_values(self):
        rows = [
            {
                "id": 1,
                "name": "Token",
                "info": {"symbol": "TKN"},
                "tags": ["defi"],
                "price": "1.50",
            }
        ]
        result = _flatten_rows(rows)
        assert result == [
            {
                "id": 1,
                "name": "Token",
                "info.symbol": "TKN",
                "tags": '["defi"]',
                "price": "1.50",
            }
        ]


class TestCsvOutput:
    def test_csv_no_python_repr(self):
        """CSV output should use JSON (double quotes) not Python repr (single quotes)."""
        data = [
            {
                "id": 1,
                "info": {"name": "Tether USD", "symbol": "USDT"},
                "tags": ["stablecoin"],
            }
        ]
        buf = io.StringIO()
        renderer = OutputRenderer()
        with patch.object(sys, "stdout", buf):
            renderer.render(data, OutputFormat.CSV)

        output = buf.getvalue()
        # Should not contain Python-style single-quoted dicts
        assert "{'name'" not in output
        assert "'symbol'" not in output
        # Flattened dict keys should appear as columns
        assert "info.name" in output
        assert "info.symbol" in output
        assert "Tether USD" in output
        # Tags should be valid JSON
        lines = output.strip().split("\n")
        assert len(lines) == 2  # header + 1 row


class TestTableOutput:
    def test_table_with_nested_data_shows_flattened_columns(self):
        """Table output should show flattened dot-notation columns."""
        from rich.console import Console

        buf = io.StringIO()
        console = Console(file=buf, width=200)
        renderer = OutputRenderer(console=console)

        data = [
            {"id": 1, "info": {"name": "Tether", "symbol": "USDT"}},
            {"id": 2, "info": {"name": "Ethereum", "symbol": "ETH"}},
        ]
        renderer.render(data, OutputFormat.TABLE)

        output = buf.getvalue()
        assert "info.name" in output
        assert "info.symbol" in output
        assert "Tether" in output
        assert "ETH" in output
