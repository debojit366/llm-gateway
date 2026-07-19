from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.services.rate_limiter import check_rate_limit


RATE_LIMIT = 5
WINDOW_SIZE = 60


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] == "http" and "/api/v1/chat/completions" in scope["path"]:

            client = scope.get("client")
            client_ip = client[0] if client else "unknown_ip"

            try:
                await check_rate_limit(
                    key=f"ip:{client_ip}",
                    limit=RATE_LIMIT,
                    window=WINDOW_SIZE
                )

            except HTTPException as e:
                response = JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)