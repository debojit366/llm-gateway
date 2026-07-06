import datetime
from app.db.mongo import db_helper
from bson import ObjectId 

async def save_request_analytics(user_id: str, client_ip: str, model: str, prompt_text: str):
    prompt_words = len(prompt_text.split())
    estimated_tokens = int(prompt_words * 1.3)
    
    cost_usd = (estimated_tokens / 1000000) * 0.075
    
    db_user_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id

    log_document = {
        "user_id": db_user_id, 
        "client_ip": client_ip,
        "model": model,
        "prompt_length": len(prompt_text),
        "tokens_used": estimated_tokens,
        "cost_usd": cost_usd,
        "timestamp": datetime.datetime.utcnow()
    }
    
    try:
        await db_helper.db.logs.insert_one(log_document)
        print(f"📊 [DB LOGGED] -> User: {user_id} | Tokens: {estimated_tokens} | Cost: ${cost_usd:.7f}")
    except Exception as e:
        print(f"❌ Failed to save analytics to Mongo: {e}")