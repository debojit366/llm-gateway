from fastapi import status
from fastapi.responses import JSONResponse
import redis
import time

try:
    r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
except Exception as e:
    print(f"Redis Connection Error: {e}")

RATE_LIMIT = 5         
WINDOW_SIZE = 60        

class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and "/api/v1/chat/completions" in scope["path"]:
            
            client = scope.get("client")
            client_ip = client[0] if client else "unknown_ip"
            
            current_time = int(time.time())
            redis_key = f"rate_limit:{client_ip}"
            
            try:
                pipe = r.pipeline()
                pipe.zremrangebyscore(redis_key, 0, current_time - WINDOW_SIZE)
                pipe.zadd(redis_key, {str(current_time): current_time})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, WINDOW_SIZE)
                
                _, _, request_count, _ = pipe.execute()
                
                if request_count > RATE_LIMIT:
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Too many requests."}
                    )
                    await response(scope, receive, send)
                    return
                    
            except Exception as e:
                print(f"Rate Limiter Redis Error: {e}")

        await self.app(scope, receive, send)