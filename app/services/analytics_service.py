from datetime import datetime, timezone
from app.db.mongo import db_helper
from bson import ObjectId 


GEMINI_PRICING = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-3-flash": {"input": 0.50, "output": 3.00},
    "gemini-3.1-pro": {"input": 2.00, "output": 12.00},
}

def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = GEMINI_PRICING.get(model, GEMINI_PRICING["gemini-2.5-flash"])  # fallback
    input_cost = (pricing["input"] / 1_000_000) * prompt_tokens
    output_cost = (pricing["output"] / 1_000_000) * completion_tokens
    return input_cost + output_cost



async def save_request_analytics(
    user_id: str, client_ip: str, model: str, prompt: str, cache_hit: bool = False,
    total_tokens: int = 0, prompt_tokens: int = 0, completion_tokens: int = 0
):
    db = getattr(db_helper, "db", None)
    if db is None:
        print("❌ Analytics Task: DB client missing")
        return

    try:
        if total_tokens == 0:
            total_tokens = len(prompt) // 4

        if cache_hit:
            cost_estimated = 0.0 
        else:
            cost_estimated = calculate_cost(model, prompt_tokens, completion_tokens)

        log_entry = {
            "user_id": user_id,
            "client_ip": client_ip,
            "model": model,
            "prompt": prompt,
            "cache_hit": cache_hit,
            "timestamp": datetime.now(timezone.utc),
            "tokens_used": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_estimated
        }

        await db.logs.insert_one(log_entry)
        print(f"✅ [ANALYTICS LOGGED] Tokens: {total_tokens} | Cost: ${cost_estimated:.8f}")

    except Exception as e:
        print(f"❌ Error while saving request analytics background task: {e}")