import secrets
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field , EmailStr
from app.db.mongo import db_helper
from datetime import datetime

router = APIRouter()

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserRegisterRequest):
    db = getattr(db_helper, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    existing_user = await db.users.find_one({"email": payload.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    api_key = f"gw_{secrets.token_urlsafe(32)}"
    
    new_user = {
        "username": payload.username,
        "email": payload.email,
        "api_key": api_key,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    result = await db.users.insert_one(new_user)
    
    return {
        "message": "User registered successfully! keep your api key safe.",
        "username": payload.username,
        "api_key": api_key
    }