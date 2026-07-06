# app/services/analytics_service.py
import datetime
from app.db.mongo import db_helper

async def save_request_analytics(client_ip: str, model: str, prompt_text: str):
    prompt_words = len(prompt_text.split())
    estimated_tokens = int(prompt_words * 1.3)
    
    cost_usd = (estimated_tokens / 1000000) * 0.075
    
    log_document = {
        "client_ip": client_ip,
        "model": model,
        "prompt_length": len(prompt_text),
        "tokens_used": estimated_tokens,
        "cost_usd": cost_usd,
        "timestamp": datetime.datetime.utcnow()
    }
    
    try:
        await db_helper.db.logs.insert_one(log_document)
        print(f"📊 [DB LOGGED] -> IP: {client_ip} | Tokens: {estimated_tokens} | Cost: ${cost_usd:.7f}")
    except Exception as e:
        print(f"❌ Failed to save analytics to Mongo: {e}")