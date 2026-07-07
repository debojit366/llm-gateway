from datetime import datetime, timezone
from app.db.mongo import db_helper
from bson import ObjectId 

async def save_request_analytics(user_id: str, client_ip: str, model: str, prompt: str, cache_hit: bool = False):
    db = getattr(db_helper, "db", None)
    if db is None:
        print("❌ Analytics Task: DB client missing")
        return

    try:
        tokens_count = len(prompt.split()) * 2
        cost_estimated = 0.0000008 * tokens_count if cache_hit else 0.000002 * tokens_count

        log_entry = {
            "user_id": user_id,
            "client_ip": client_ip,
            "model": model,
            "prompt": prompt,
            "cache_hit": cache_hit,
            "timestamp": datetime.now(timezone.utc),
            "tokens_used": tokens_count,
            "cost_usd": cost_estimated
        }
        
        await db.logs.insert_one(log_entry)
        print(f"✅ [ANALYTICS LOGGED SUCCESSFULLY] Cache Hit: {cache_hit}")
        
    except Exception as e:
        print(f"❌ Error while saving request analytics background task: {e}")