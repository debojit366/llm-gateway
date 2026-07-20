# app/services/cache_service.py
import redis.asyncio as aioredis
import hashlib
import uuid
from app.core.config import settings
from app.services.embedding_service import get_embedding
from app.db.qdrant_client import qdrant_client, COLLECTION_NAME
from qdrant_client.models import PointStruct

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)


def get_prompt_hash(prompt: str) -> str:
    return hashlib.md5(prompt.strip().lower().encode("utf-8")).hexdigest()


def get_point_id(prompt_hash: str) -> str:
    
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, prompt_hash))


async def check_semantic_cache(prompt: str, threshold: float = 0.88):
    prompt_clean = prompt.strip().lower()
    prompt_hash = get_prompt_hash(prompt_clean)

    # LAYER 1: Redis exact match
    try:
        cached_response = await redis_client.get(f"cache:exact:{prompt_hash}")
        if cached_response:
            print("🔥 [REDIS EXACT CACHE HIT]")
            return cached_response, 1.0
    except Exception as e:
        print(f"⚠️ Redis read error: {e}")

    # LAYER 2: Qdrant semantic vector lookup
    try:
        query_vector = await get_embedding(prompt_clean)
        if not query_vector:
            print("⚠️ Embedding generation failed, skipping semantic cache.")
            return None, 0.0

        results = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=1,
            with_payload=True
        ).points

        if results:
            best_match = results[0]
            score = best_match.score

            if score >= threshold:
                cached_text = best_match.payload["response_text"]

                try:
                    await redis_client.setex(f"cache:exact:{prompt_hash}", 86400, cached_text)
                except Exception:
                    pass

                print(f"🧠 [QDRANT SEMANTIC HIT] Score: {score:.4f} | Prompt: '{best_match.payload.get('prompt')}'")
                return cached_text, score

    except Exception as e:
        print(f"⚠️ Semantic Cache Lookup Error: {e}")

    return None, 0.0


async def save_to_semantic_cache(prompt: str, response_text: str):
    if not prompt.strip() or not response_text.strip():
        return

    prompt_clean = prompt.strip().lower()
    prompt_hash = get_prompt_hash(prompt_clean)
    point_id = get_point_id(prompt_hash)  

    try:
        await redis_client.setex(f"cache:exact:{prompt_hash}", 86400, response_text)
        print(f"💾 [REDIS CACHE SAVED] Hash: {prompt_hash}")

        embedding = await get_embedding(prompt_clean)

        if embedding:
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,         
                        vector=embedding,
                        payload={
                            "prompt": prompt,
                            "prompt_hash": prompt_hash, 
                            "response_text": response_text
                        }
                    )
                ]
            )
            print(f"💾 [QDRANT CACHE SAVED] Prompt: '{prompt}'")
        else:
            print("❌ Failed to save semantic cache — empty embedding.")

    except Exception as e:
        print(f"⚠️ Error while saving cache layer: {e}")