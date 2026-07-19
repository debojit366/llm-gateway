from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.db.mongo import db_helper
from typing import Dict, Any
from datetime import datetime, timedelta
from app.services.rate_limiter import check_rate_limit

API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 10



async def verify_api_key(api_key_header: str = Security(API_KEY_HEADER)) -> Dict[str, Any]:
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header missing !"
        )
        
    db = getattr(db_helper, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection error")
        
    user = await db.users.find_one({"api_key": api_key_header, "is_active": True})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or Deactivated API Key!"
        )
    await check_rate_limit(
    key=f"user:{user['_id']}",
    limit=10,
    window=60
)
        
    return user 