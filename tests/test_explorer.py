from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import rich_click as click

from cli.commands.explorer import _run_async_and_poll
from cli.constants.config import EXIT_ERROR
from cli.types.context import CliContext


def _response(status_code: int, body: dict | None = None, text: str = ""):
    payload = body or {}

    def json_fn():
        return payload

    return SimpleNamespace(status_code=status_code, json=json_fn, text=text)


def _click_ctx(*, verbose: bool = False) -> click.Context:
    ctx = click.Context(click.Command("test"))
    ctx.obj = CliContext(verbose=verbose)
    return ctx


class MockExplorerClient:
    """Minimal async client stub for explorer polling tests."""

    def __init__(
        self,
        *,
        run_id: str = "run-123",
        status_sequence: list[str] | None = None,
    ) -> None:
        self.run_id = run_id
        self.status_sequence = list(status_sequence or ["success"])
        self.get_paths: list[str] = []

    async def post(self, endpoint: str, json: dict | None = None) -> SimpleNamespace:
        return _response(200, {"run_id": self.run_id})

    async def get(self, path: str, params: dict | None = None) -> SimpleNamespace:
        self.get_paths.append(path)
        if path.endswith("/status"):
            status = self.status_sequence.pop(0)
            return _response(200, {"status": status})
        if path.endswith("/error"):
            return _response(200, {"message": "syntax error"})
        if path.endswith("/results"):
            return _response(200, {"items": [{"id": 1}]})
        raise AssertionError(f"unexpected GET {path}")


@pytest.mark.parametrize("terminal_status", ["failed", "canceled"])
def test_run_async_and_poll_exits_on_terminal_failure(terminal_status: str) -> None:
    ctx = _click_ctx()
    client = MockExplorerClient(status_sequence=[terminal_status])

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(
            _run_async_and_poll(
                ctx,
                client,
                "/api/v1/explorer/queries/run-async",
                {"parameters": {"sql": "SELECT 1"}},
                no_wait=False,
            )
        )

    assert exc_info.value.code == EXIT_ERROR
    assert not any(p.endswith("/results") for p in client.get_paths)


def test_run_async_and_poll_exits_on_poll_timeout() -> None:
    ctx = _click_ctx()
    client = MockExplorerClient(status_sequence=["running"])

    with (
        patch("cli.commands.explorer.MAX_POLL_TIME", 0.0),
        patch("cli.commands.explorer.asyncio.sleep", new_callable=AsyncMock),
        patch("cli.commands.explorer.asyncio.get_event_loop") as mock_get_loop,
        pytest.raises(SystemExit) as exc_info,
    ):
        loop = MagicMock()
        loop.time.side_effect = [0.0, 1.0]
        mock_get_loop.return_value = loop

        asyncio.run(
            _run_async_and_poll(
                ctx,
                client,
                "/api/v1/explorer/queries/run-async",
                {"parameters": {"sql": "SELECT 1"}},
                no_wait=False,
            )
        )

    assert exc_info.value.code == EXIT_ERROR
    assert not any(p.endswith("/results") for p in client.get_paths)


def test_run_async_and_poll_fetches_results_on_success() -> None:
    ctx = _click_ctx()
    client = MockExplorerClient(status_sequence=["success"])
    fetch = AsyncMock()

    with patch("cli.commands.explorer._fetch_and_display_results", fetch):
        asyncio.run(
            _run_async_and_poll(
                ctx,
                client,
                "/api/v1/explorer/queries/run-async",
                {"parameters": {"sql": "SELECT 1"}},
                no_wait=False,
            )
        )

    fetch.assert_awaited_once_with(ctx, client, "run-123")


def test_run_async_and_poll_no_wait_does_not_poll() -> None:
    ctx = _click_ctx()
    client = MockExplorerClient()

    with patch(
        "cli.commands.explorer._poll_until_done", new_callable=AsyncMock
    ) as poll:
        asyncio.run(
            _run_async_and_poll(
                ctx,
                client,
                "/api/v1/explorer/queries/run-async",
                {"parameters": {"sql": "SELECT 1"}},
                no_wait=True,
            )
        )

    poll.assert_not_awaited()
    assert not client.get_paths
