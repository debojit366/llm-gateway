# app/db/qdrant_client.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

COLLECTION_NAME = "semantic_cache"
VECTOR_SIZE = 768 

qdrant_client = QdrantClient(url=settings.QDRANT_URL)

existing_collections = [c.name for c in qdrant_client.get_collections().collections]
if COLLECTION_NAME not in existing_collections:
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )