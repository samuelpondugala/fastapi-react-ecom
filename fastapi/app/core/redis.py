from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis | None:
    settings = get_settings()
    if not settings.REDIS_ENABLED:
        return None

    try:
        client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
            health_check_interval=30,
        )
        client.ping()
        return client
    except RedisError as exc:
        logger.warning("Redis unavailable; continuing without Redis features: %s", exc)
        return None


def redis_get_json(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None

    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except (RedisError, json.JSONDecodeError) as exc:
        logger.warning("Redis get_json failed for key=%s: %s", key, exc)
        return None


def redis_set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    client = get_redis_client()
    if client is None:
        return False

    try:
        payload = json.dumps(value, default=str, separators=(",", ":"))
        client.setex(key, max(1, ttl_seconds), payload)
        return True
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("Redis set_json failed for key=%s: %s", key, exc)
        return False


def redis_delete(key: str) -> None:
    client = get_redis_client()
    if client is None:
        return

    try:
        client.delete(key)
    except RedisError as exc:
        logger.warning("Redis delete failed for key=%s: %s", key, exc)


def redis_delete_pattern(pattern: str) -> int:
    client = get_redis_client()
    if client is None:
        return 0

    deleted = 0
    try:
        for key in client.scan_iter(match=pattern, count=200):
            deleted += int(client.delete(key) or 0)
    except RedisError as exc:
        logger.warning("Redis delete_pattern failed for pattern=%s: %s", pattern, exc)
    return deleted
