from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.db.mongo import db_helper
from typing import Dict, Any

API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key_header: str = Security(API_KEY_HEADER)) -> Dict[str, Any]:
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header missing hai bhai!"
        )
        
    db = getattr(db_helper, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection error")
        
    user = await db.users.find_one({"api_key": api_key_header, "is_active": True})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ya Deactivated API Key!"
        )
        
    return user 