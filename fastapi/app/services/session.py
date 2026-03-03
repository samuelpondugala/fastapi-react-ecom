from __future__ import annotations

import secrets
import time

from app.core.config import get_settings
from app.core.redis import redis_delete, redis_get_json, redis_set_json


def _session_key(session_id: str) -> str:
    settings = get_settings()
    return f"{settings.SESSION_REDIS_PREFIX}{session_id}"


def create_session_for_user(user_id: int) -> str | None:
    settings = get_settings()
    if not settings.REDIS_ENABLED:
        return None

    session_id = secrets.token_urlsafe(32)
    payload = {
        "user_id": user_id,
        "created_at": int(time.time()),
    }
    ok = redis_set_json(_session_key(session_id), payload, settings.SESSION_TTL_SECONDS)
    return session_id if ok else None


def get_user_id_from_session(session_id: str | None) -> int | None:
    if not session_id:
        return None

    payload = redis_get_json(_session_key(session_id))
    if not isinstance(payload, dict):
        return None

    user_id = payload.get("user_id")
    if isinstance(user_id, int):
        return user_id
    if isinstance(user_id, str) and user_id.isdigit():
        return int(user_id)
    return None


def delete_session(session_id: str | None) -> None:
    if not session_id:
        return
    redis_delete(_session_key(session_id))
