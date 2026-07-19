import time
import redis
from fastapi import HTTPException

r = redis.Redis(
    host="redis",
    port=6379,
    db=0,
    decode_responses=True
)


async def check_rate_limit(
    key: str,
    limit: int,
    window: int
):
    current_time = time.time()

    pipe = r.pipeline()

    pipe.zremrangebyscore(
        key,
        0,
        current_time - window
    )

    pipe.zadd(
        key,
        {str(current_time): current_time}
    )

    pipe.zcard(key)

    pipe.expire(
        key,
        window
    )

    _, _, request_count, _ = pipe.execute()

    if request_count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests."
        )