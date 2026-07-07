# app/services/cache_service.py
import numpy as np
import redis.asyncio as aioredis
import hashlib
from app.core.config import settings
from app.services.embedding_service import get_embedding

# Redis Client Setup
redis_client = aioredis.from_url(
    "redis://redis:6379", 
    encoding="utf-8", 
    decode_responses=True
)

def get_prompt_hash(prompt: str) -> str:
    return hashlib.md5(prompt.strip().lower().encode("utf-8")).hexdigest()

def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0
    return dot_product / (norm_v1 * norm_v2)

async def check_semantic_cache(prompt: str, threshold: float = 0.88):
    from app.db.mongo import db_helper 
    
    prompt_clean = prompt.strip().lower()
    prompt_hash = get_prompt_hash(prompt_clean)
    
    # -------------------------------------------------------------
    # LAYER 1: REDIS EXACT MATCH LOOKUP
    # -------------------------------------------------------------
    try:
        cached_response = await redis_client.get(f"cache:exact:{prompt_hash}")
        if cached_response:
            print(f"🔥 [REDIS EXACT CACHE HIT] Served instantly via Redis String Match!")
            return cached_response, 1.0
    except Exception as e:
        print(f"⚠️ Redis read error: {e}")

    # -------------------------------------------------------------
    #  LAYER 2: MONGODB SEMANTIC VECTOR LOOKUP
    # -------------------------------------------------------------
    try:
        query_vector = await get_embedding(prompt_clean)
        
        if not query_vector:
            print("⚠️ Cache system skipped because embedding generation failed.")
            return None, 0.0
            
        cache_records = await db_helper.client["llm_gateway_db"]["semantic_cache"].find({}).to_list(length=2000)
        
        best_match = None
        highest_score = -1.0
        
        for record in cache_records:
            cached_vector = record.get("embedding")
            if not cached_vector:
                continue
                
            score = cosine_similarity(query_vector, cached_vector)
            if score > highest_score:
                highest_score = score
                best_match = record
                
        if highest_score >= threshold and best_match:
            cached_text = best_match["response_text"]
            
            try:
                await redis_client.setex(f"cache:exact:{prompt_hash}", 86400, cached_text)
            except Exception:
                pass
                
            print(f"🧠 [MONGO SEMANTIC HIT] Score: {highest_score:.4f} | Prompt Match: '{best_match['prompt']}'")
            return cached_text, highest_score

    except Exception as e:
        print(f"⚠️ Semantic Cache Lookup Error: {e}")
        
    return None, 0.0

async def save_to_semantic_cache(prompt: str, response_text: str):
    from app.db.mongo import db_helper 
    
    if not prompt.strip() or not response_text.strip():
        return
        
    prompt_clean = prompt.strip().lower()
    prompt_hash = get_prompt_hash(prompt_clean)
    
    try:
        await redis_client.setex(f"cache:exact:{prompt_hash}", 86400, response_text)
        print(f"💾 [REDIS CACHE SAVED] Prompt Exact Hash: {prompt_hash}")
        
        embedding = await get_embedding(prompt_clean)
        
        if embedding:
            cache_document = {
                "prompt": prompt,
                "prompt_hash": prompt_hash,
                "response_text": response_text,
                "embedding": embedding
            }
            
            await db_helper.client["llm_gateway_db"]["semantic_cache"].insert_one(cache_document)
            print(f"💾 [MONGO SEMANTIC CACHE SAVED] Prompt: '{prompt}'")
        else:
            print("❌ Failed to save semantic cache due to empty embedding output.")
        
    except Exception as e:
        print(f"⚠️ Error while saving cache layer: {e}")