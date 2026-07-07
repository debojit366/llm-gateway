# app/services/cache_service.py
import math
import app.db.mongo as mongo 
from app.services.embedding_service import get_embedding

SIMILARITY_THRESHOLD = 0.88 

def cosine_similarity(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
        
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot_product / (norm_a * norm_b)

async def check_semantic_cache(prompt: str):
    current_vector = await get_embedding(prompt)
    if not current_vector:
        return None, None

    try:
        db_instance = mongo.db_helper.db
        
        if db_instance is None:
            print("⚠️ MongoDB 'db' instance is not initialized yet in db_helper! Skipping cache lookup.")
            return None, None
            
        cache_records = await db_instance.semantic_cache.find({}).to_list(length=1000)
        
        best_match = None
        highest_score = 0.0
        
        for record in cache_records:
            saved_vector = record.get("embedding")
            score = cosine_similarity(current_vector, saved_vector)
            
            if score > highest_score:
                highest_score = score
                best_match = record
                
        if highest_score >= SIMILARITY_THRESHOLD:
            print(f"🔥 [SEMANTIC CACHE HIT] Score: {highest_score:.4f} | Prompt Match: '{best_match['prompt']}'")
            return best_match["response"], highest_score
            
    except Exception as e:
        print(f"⚠️ Cache Lookup Error: {e}")
        
    return None, None

async def save_to_semantic_cache(prompt: str, response_text: str):
    vector = await get_embedding(prompt)
    if not vector:
        return
        
    try:
        db_instance = mongo.db_helper.db
        if db_instance is None:
            print("⚠️ MongoDB 'db' instance is not initialized yet in db_helper! Cannot save cache.")
            return
            
        cache_document = {
            "prompt": prompt,
            "embedding": vector,
            "response": response_text
        }
        await db_instance.semantic_cache.insert_one(cache_document)
        print(f"💾 [SEMANTIC CACHE SAVED] Prompt: '{prompt}'")
    except Exception as e:
        print(f"❌ Cache Save Error: {e}")