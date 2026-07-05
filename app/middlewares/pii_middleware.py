# app/middleware/pii_middleware.py
from fastapi import Request
from app.utils.pii_masker import mask_pii_data
import json

class PIIMaskingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST" and "/api/v1/chat/completions" in scope["path"]:
            
            body_chunks = []
            
            async def receive_with_masking():
                nonlocal body_chunks
                message = await receive()
                
                if message["type"] == "http.request":
                    body_chunks.append(message.get("body", b""))
                    
                    if not message.get("more_body", False):
                        full_body = b"".join(body_chunks)
                        try:
                            body_json = json.loads(full_body.decode("utf-8"))
                            
                            if "messages" in body_json:
                                for msg in body_json["messages"]:
                                    if "content" in msg:
                                        msg["content"] = mask_pii_data(msg["content"])
                            
                            modified_body = json.dumps(body_json).encode("utf-8")
                            message["body"] = modified_body
                        except Exception:
                            message["body"] = full_body
                            
                return message

            await self.app(scope, receive_with_masking, send)
        else:
            await self.app(scope, receive, send)