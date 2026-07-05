# app/main.py
from fastapi import FastAPI
from app.api.v1.endpoints import chat
import httpx
from app.middlewares.pii_middleware import PIIMaskingMiddleware 
app = FastAPI(title="Intelligent Gemini AI Gateway", version="1.0.0")
app.add_middleware(PIIMaskingMiddleware)
@app.on_event("startup")
async def startup_event():
    app.state.http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "provider": "gemini-active"}

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])