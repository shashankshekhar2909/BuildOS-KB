from redis.asyncio import Redis, ConnectionPool
from app.config import settings

_pool: ConnectionPool | None = None
_redis: Redis | None = None


async def get_redis() -> Redis:
    global _pool, _redis
    if _redis is None:
        _pool = ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
        _redis = Redis(connection_pool=_pool)
    return _redis


async def close_redis() -> None:
    global _redis, _pool
    if _redis:
        await _redis.aclose()
        _redis = None
    if _pool:
        await _pool.aclose()
        _pool = None
