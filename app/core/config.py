# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    
    GEMINI_API_KEY: str = ""  
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    REDIS_URL: str = "redis://redis:6379/0"
    QDRANT_URL: str = "http://qdrant:6333"

    class Config:
        env_file = ".env"

settings = Settings()