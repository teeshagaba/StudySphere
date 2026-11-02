import time

from redis.asyncio import Redis

from .config import settings


class MemoryCache:
    """Single-process stand-in for the Redis calls we use (dev only)."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[object, float | None]] = {}

    def _live(self, key: str):
        item = self._data.get(key)
        if item and item[1] is not None and item[1] < time.time():
            del self._data[key]
            return None
        return item

    async def get(self, key: str):
        item = self._live(key)
        return item[0] if item else None

    async def set(self, key: str, value, ex: int | None = None) -> None:
        self._data[key] = (value, time.time() + ex if ex else None)

    async def incr(self, key: str) -> int:
        item = self._live(key)
        value = int(item[0]) + 1 if item else 1
        self._data[key] = (value, item[1] if item else None)
        return value

    async def expire(self, key: str, seconds: int) -> None:
        if item := self._live(key):
            self._data[key] = (item[0], time.time() + seconds)


redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else MemoryCache()
