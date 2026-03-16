from __future__ import annotations

import json
import time
from importlib.metadata import version as pkg_version

from cli.constants.config import CONFIG_DIR
from cli.utils.console import err_console

_VERSION_CACHE = CONFIG_DIR / ".version_check"
_CHECK_INTERVAL = 86400  # 24h


def check_for_updates() -> None:
    """print a one-liner to stderr if a newer version is on PyPI. never raises."""
    try:
        now = time.time()
        if _VERSION_CACHE.exists():
            cache = json.loads(_VERSION_CACHE.read_text())
            if now - cache.get("ts", 0) < _CHECK_INTERVAL:
                if cache.get("latest") and cache["latest"] != cache.get("current"):
                    err_console.print(
                        f"[dim]Update available: {cache['current']}"
                        f" → {cache['latest']}."
                        " Run: pip install -U allium-cli[/dim]"
                    )
                return

        import httpx

        current = pkg_version("allium-cli")
        resp = httpx.get("https://pypi.org/pypi/allium-cli/json", timeout=2.0)
        latest = resp.json()["info"]["version"] if resp.status_code == 200 else current

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _VERSION_CACHE.write_text(
            json.dumps({"ts": now, "current": current, "latest": latest})
        )

        if latest != current:
            err_console.print(
                f"[dim]Update available: {current} → {latest}."
                " Run: pip install -U allium-cli[/dim]"
            )
    except Exception:
        pass
