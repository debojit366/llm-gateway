# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    
    OPENAI_API_KEY: str = "your-openai-api-key-here"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"

    class Config:
        env_file = ".env"

settings = Settings()