from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.redis import redis_delete_pattern, redis_get_json, redis_set_json


def _prefix(namespace: str) -> str:
    settings = get_settings()
    return f"{settings.CACHE_REDIS_PREFIX}{namespace}:"


def _build_key(namespace: str, **params: Any) -> str:
    base = _prefix(namespace)
    if not params:
        return f"{base}default"

    parts: list[str] = []
    for key in sorted(params):
        value = params[key]
        normalized = "" if value is None else str(value)
        parts.append(f"{key}={normalized}")
    return f"{base}{'|'.join(parts)}"


def get_cached(namespace: str, **params: Any) -> Any | None:
    settings = get_settings()
    if not settings.REDIS_ENABLED:
        return None
    return redis_get_json(_build_key(namespace, **params))


def set_cached(namespace: str, value: Any, ttl_seconds: int | None = None, **params: Any) -> bool:
    settings = get_settings()
    if not settings.REDIS_ENABLED:
        return False

    ttl = settings.CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    return redis_set_json(_build_key(namespace, **params), value, ttl)


def invalidate_namespace(namespace: str) -> int:
    settings = get_settings()
    if not settings.REDIS_ENABLED:
        return 0
    return redis_delete_pattern(f"{_prefix(namespace)}*")
