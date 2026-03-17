from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from cli.utils.body import load_body_or_build, pair_chain_items
from cli.utils.errors import format_api_error


class TestFormatApiError:
    def _response(self, status_code: int, body: dict | str | None = None):
        ns = SimpleNamespace(status_code=status_code)
        if body is not None:
            if isinstance(body, dict):
                ns.json = lambda: body
                ns.text = json.dumps(body)
            else:
                ns.json = lambda: (_ for _ in ()).throw(ValueError("no json"))
                ns.text = body
        else:
            ns.json = lambda: (_ for _ in ()).throw(ValueError("no json"))
            ns.text = ""
        return ns

    def test_extracts_message_key(self):
        resp = self._response(400, {"message": "bad request"})
        assert format_api_error(resp) == "bad request"

    def test_extracts_detail_key(self):
        resp = self._response(403, {"detail": "forbidden"})
        assert format_api_error(resp) == "forbidden"

    def test_extracts_error_key(self):
        resp = self._response(500, {"error": "internal"})
        assert format_api_error(resp) == "internal"

    def test_falls_back_to_json_dump(self):
        resp = self._response(400, {"foo": "bar"})
        result = format_api_error(resp)
        assert "foo" in result
        assert "bar" in result

    def test_non_json_response(self):
        resp = self._response(502, "Bad Gateway")
        assert format_api_error(resp) == "Bad Gateway"

    def test_empty_body(self):
        resp = self._response(500)
        assert format_api_error(resp) == "HTTP 500"


class TestPairChainItems:
    def test_basic_pairing(self):
        result = pair_chain_items(("ethereum",), ("0xabc",))
        assert result == [{"chain": "ethereum", "address": "0xabc"}]

    def test_multiple_pairs(self):
        result = pair_chain_items(
            ("ethereum", "solana"),
            ("0xabc", "So111"),
        )
        assert len(result) == 2
        assert result[1]["chain"] == "solana"

    def test_custom_keys(self):
        result = pair_chain_items(
            ("ethereum",),
            ("0xtoken",),
            chain_key="blockchain",
            address_key="token_address",
        )
        assert result[0]["blockchain"] == "ethereum"
        assert result[0]["token_address"] == "0xtoken"

    def test_empty_chains_raises(self):
        from click import UsageError

        with pytest.raises(UsageError, match="--chain"):
            pair_chain_items((), ("0xabc",))

    def test_mismatched_lengths_raises(self):
        from click import UsageError

        with pytest.raises(UsageError, match="Mismatched"):
            pair_chain_items(("ethereum", "solana"), ("0xabc",))


class TestLoadBodyOrBuild:
    def test_inline_json(self):
        result = load_body_or_build('[{"chain": "ethereum"}]', lambda: None)
        assert result == [{"chain": "ethereum"}]

    def test_file_json(self, tmp_path):
        f = tmp_path / "body.json"
        f.write_text('{"key": "value"}')
        result = load_body_or_build(str(f), lambda: None)
        assert result == {"key": "value"}

    def test_invalid_json_raises_usage_error(self):
        from click import UsageError

        with pytest.raises(UsageError, match="Invalid JSON"):
            load_body_or_build("not-json{{{", lambda: None)

    def test_fallback_to_build_fn(self):
        result = load_body_or_build(None, lambda: {"built": True})
        assert result == {"built": True}
