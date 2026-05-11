"""按用户维度的会话计数；优先 Redis，未配置或连接失败时回退内存。"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SessionStore(ABC):
    @abstractmethod
    def snapshot(self, user_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def increment_clarify(self, user_id: str) -> int:
        ...

    @abstractmethod
    def reset_clarify(self, user_id: str) -> None:
        ...

    @abstractmethod
    def increment_retry(self, user_id: str) -> int:
        ...

    @abstractmethod
    def reset_retry(self, user_id: str) -> None:
        ...


class MemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def snapshot(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self._data:
            self._data[user_id] = {"clarify_count": 0, "retry_count": 0}
        return dict(self._data[user_id])

    def increment_clarify(self, user_id: str) -> int:
        s = self.snapshot(user_id)
        s["clarify_count"] = int(s.get("clarify_count", 0)) + 1
        self._data[user_id].update(s)
        return s["clarify_count"]

    def reset_clarify(self, user_id: str) -> None:
        if user_id in self._data:
            self._data[user_id]["clarify_count"] = 0

    def increment_retry(self, user_id: str) -> int:
        s = self.snapshot(user_id)
        s["retry_count"] = int(s.get("retry_count", 0)) + 1
        self._data[user_id].update(s)
        return s["retry_count"]

    def reset_retry(self, user_id: str) -> None:
        if user_id in self._data:
            self._data[user_id]["retry_count"] = 0


class RedisSessionStore(SessionStore):
    def __init__(self, url: str, key_prefix: str, ttl_seconds: int) -> None:
        import redis

        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._client.ping()
        self._prefix = key_prefix
        self._ttl = ttl_seconds

    def _key(self, user_id: str) -> str:
        return f"{self._prefix}session:{user_id}"

    def _load(self, user_id: str) -> Dict[str, Any]:
        raw = self._client.get(self._key(user_id))
        if not raw:
            return {"clarify_count": 0, "retry_count": 0}
        try:
            data = json.loads(raw)
            return {
                "clarify_count": int(data.get("clarify_count", 0)),
                "retry_count": int(data.get("retry_count", 0)),
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            return {"clarify_count": 0, "retry_count": 0}

    def _save(self, user_id: str, data: Dict[str, Any]) -> None:
        key = self._key(user_id)
        self._client.set(key, json.dumps(data))
        if self._ttl > 0:
            self._client.expire(key, self._ttl)

    def snapshot(self, user_id: str) -> Dict[str, Any]:
        return dict(self._load(user_id))

    def increment_clarify(self, user_id: str) -> int:
        data = self._load(user_id)
        data["clarify_count"] = data["clarify_count"] + 1
        self._save(user_id, data)
        return data["clarify_count"]

    def reset_clarify(self, user_id: str) -> None:
        data = self._load(user_id)
        data["clarify_count"] = 0
        self._save(user_id, data)

    def increment_retry(self, user_id: str) -> int:
        data = self._load(user_id)
        data["retry_count"] = data["retry_count"] + 1
        self._save(user_id, data)
        return data["retry_count"]

    def reset_retry(self, user_id: str) -> None:
        data = self._load(user_id)
        data["retry_count"] = 0
        self._save(user_id, data)


def _build_session_store() -> SessionStore:
    try:
        from app.config.settings import REDIS_KEY_PREFIX, REDIS_SESSION_TTL, REDIS_URL
    except ImportError:
        logger.warning("settings import failed, using MemorySessionStore")
        return MemorySessionStore()

    if not REDIS_URL:
        logger.info("REDIS_URL unset, using MemorySessionStore for sessions")
        return MemorySessionStore()

    try:
        store = RedisSessionStore(
            REDIS_URL,
            key_prefix=REDIS_KEY_PREFIX,
            ttl_seconds=REDIS_SESSION_TTL,
        )
        logger.info(
            "session store: Redis (prefix=%s ttl=%ss)",
            REDIS_KEY_PREFIX,
            REDIS_SESSION_TTL,
        )
        return store
    except Exception as e:
        logger.warning(
            "Redis unavailable (%s), falling back to MemorySessionStore",
            e,
        )
        return MemorySessionStore()


session_store: SessionStore = _build_session_store()
