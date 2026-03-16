from __future__ import annotations

from cli.types.profiles import ApiKeyProfile


def get_headers(profile: ApiKeyProfile) -> dict[str, str]:
    return {"X-API-Key": profile.api_key}
