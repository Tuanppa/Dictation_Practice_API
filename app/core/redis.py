import redis
from typing import Any
from app.core.config import settings

# Tạo Redis connection pool
# Railway cung cấp REDIS_URL, fallback về REDIS_HOST/PORT cho local
if settings.REDIS_URL:
    # Production: dùng REDIS_URL từ Railway
    redis_client: redis.Redis[Any] = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )
else:
    # Development: dùng REDIS_HOST/PORT
    redis_client: redis.Redis[Any] = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )


def get_redis() -> redis.Redis[Any]:
    """
    Get Redis client instance
    
    Returns:
        redis.Redis: Redis client
    """
    return redis_client
