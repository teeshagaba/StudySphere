import logging
import time

from fastapi import HTTPException
from redis.exceptions import RedisError

from ..cache import redis

log = logging.getLogger(__name__)


async def enforce(user_id: int | str, bucket: str, limit: int, window_seconds: int = 60) -> None:
    key = f"rl:{bucket}:{user_id}:{int(time.time() // window_seconds)}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
    except RedisError as e:
        log.warning("Rate limiter unavailable: %s", e)
        return
    if count > limit:
        raise HTTPException(429, "Too many requests, slow down a little")
