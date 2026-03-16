from __future__ import annotations

import asyncio
import functools
from typing import Any


def async_command(f: Any) -> Any:
    """wrap an async click handler so click sees a sync function."""

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper
