# app/main.py
from fastapi import FastAPI
from app.api.v1.endpoints import chat,analytics
import httpx
from app.middlewares.pii_middleware import PIIMaskingMiddleware 
from app.middlewares.rate_limit_middleware import RateLimitMiddleware
from app.db.mongo import connect_to_mongo, close_mongo_connection



app = FastAPI(title="Intelligent Gemini AI Gateway", version="1.0.0")
app.add_middleware(PIIMaskingMiddleware)
app.add_middleware(RateLimitMiddleware)
@app.on_event("startup")
async def startup_event():
    app.state.http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )
    await connect_to_mongo()
@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()
    await close_mongo_connection()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "provider": "gemini-active"}

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])