from __future__ import annotations

from decimal import Decimal

import pytest

from cli.utils.cost_log import CostLog, _to_human_amount


@pytest.fixture()
def log(tmp_path):
    """Return a CostLog pointed at a temp directory."""
    return CostLog(log_file=tmp_path / "cost_log.csv")


class TestToHumanAmount:
    def test_basic_conversion(self):
        assert _to_human_amount("1000000") == "1.000000"

    def test_zero(self):
        assert _to_human_amount("0") == "0.000000"

    def test_small_amount(self):
        assert _to_human_amount("100") == "0.000100"

    def test_string_passthrough_on_invalid(self):
        assert _to_human_amount("not-a-number") == "not-a-number"

    def test_custom_decimals(self):
        assert _to_human_amount("1000000000000000000", decimals=18) == (
            "1.000000000000000000"
        )


class TestLogAndRead:
    def test_log_creates_file_and_reads(self, log):
        log.log_payment(
            method="x402",
            endpoint="/api/v1/test",
            network="eip155:8453",
            raw_amount="500000",
            token="USDC",
            wallet="0xabc",
            http_status=200,
        )
        rows = log.read()
        assert len(rows) == 1
        assert rows[0]["method"] == "x402"
        assert rows[0]["amount"] == "0.500000"
        assert rows[0]["endpoint"] == "/api/v1/test"

    def test_multiple_entries(self, log):
        for i in range(5):
            log.log_payment(
                method="tempo",
                endpoint=f"/api/v1/test/{i}",
                network="42431",
                raw_amount=str(100000 * (i + 1)),
                token="tempo",
                wallet="tempo-account",
                http_status=200,
            )
        assert len(log.read()) == 5

    def test_read_with_limit(self, log):
        for i in range(10):
            log.log_payment(
                method="x402",
                endpoint="/test",
                network="eip155:8453",
                raw_amount=str(i * 100000),
                token="USDC",
                wallet="0xabc",
                http_status=200,
            )
        rows = log.read(limit=3)
        assert len(rows) == 3

    def test_read_empty_log(self, log):
        assert log.read() == []


class TestTotalCost:
    def test_groups_by_method_and_network(self, log):
        log.log_payment(
            method="x402",
            endpoint="/a",
            network="eip155:8453",
            raw_amount="1000000",
            token="USDC",
            wallet="0x1",
            http_status=200,
        )
        log.log_payment(
            method="x402",
            endpoint="/b",
            network="eip155:8453",
            raw_amount="2000000",
            token="USDC",
            wallet="0x1",
            http_status=200,
        )
        log.log_payment(
            method="tempo",
            endpoint="/c",
            network="42431",
            raw_amount="500000",
            token="tempo",
            wallet="tempo",
            http_status=200,
        )
        totals = log.total()
        assert totals["x402:eip155:8453"]["calls"] == 2
        assert totals["x402:eip155:8453"]["amount"] == Decimal("3.000000")
        assert totals["tempo:42431"]["calls"] == 1

    def test_empty_log(self, log):
        assert log.total() == {}


class TestClearLog:
    def test_clear_existing(self, log):
        log.log_payment(
            method="x402",
            endpoint="/test",
            network="eip155:8453",
            raw_amount="100",
            token="USDC",
            wallet="0x1",
            http_status=200,
        )
        assert log.clear() is True
        assert log.read() == []

    def test_clear_nonexistent(self, log):
        assert log.clear() is False
