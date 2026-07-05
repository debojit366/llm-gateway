# app/middlewares/pii_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from app.utils.pii_masker import mask_pii_data
import json

class PIIMaskingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and "/api/v1/chat/completions" in request.url.path:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_json = json.loads(body_bytes.decode("utf-8"))
                    
                    if "messages" in body_json:
                        for msg in body_json["messages"]:
                            if "content" in msg:
                                msg["content"] = mask_pii_data(msg["content"])
                    
                    async def receive():
                        return {"type": "http.request", "body": json.dumps(body_json).encode("utf-8")}
                    
                    request._receive = receive
            except Exception as e:
                pass

        response = await call_next(request)
        return response