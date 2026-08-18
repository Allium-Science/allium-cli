"""CSV and table output must handle heterogeneous response rows.

Regression tests for #19: columns came from rows[0].keys() only, so CSV
output raised ValueError when a later row carried an extra field, and
table output silently dropped that column.
"""

from __future__ import annotations

import csv
import io

import pytest

from cli.types.enums import OutputFormat
from cli.utils.output import OutputRenderer, _union_columns

HETEROGENEOUS = [
    {"address": "0xabc", "chain": "ethereum"},
    {"address": "0xdef", "chain": "solana", "token_id": "42"},
    {"address": "0x123", "chain": "base", "usd_value": "19.99"},
]


class TestUnionColumns:
    def test_first_seen_order_across_all_rows(self):
        assert _union_columns(HETEROGENEOUS) == [
            "address",
            "chain",
            "token_id",
            "usd_value",
        ]

    def test_homogeneous_rows_unchanged(self):
        rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        assert _union_columns(rows) == ["a", "b"]


class TestCsvOutput:
    def test_extra_fields_do_not_crash_and_reach_the_output(self, capsys):
        OutputRenderer().render(HETEROGENEOUS, OutputFormat.CSV)
        out = capsys.readouterr().out
        reader = list(csv.DictReader(io.StringIO(out)))
        assert reader[0].keys() == {"address", "chain", "token_id", "usd_value"}
        assert reader[1]["token_id"] == "42"
        assert reader[2]["usd_value"] == "19.99"

    def test_missing_fields_render_empty_not_error(self, capsys):
        OutputRenderer().render(HETEROGENEOUS, OutputFormat.CSV)
        out = capsys.readouterr().out
        reader = list(csv.DictReader(io.StringIO(out)))
        assert reader[0]["token_id"] == ""
        assert reader[0]["usd_value"] == ""
