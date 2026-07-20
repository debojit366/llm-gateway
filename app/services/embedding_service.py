import asyncio
from google import genai
from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def get_embedding(text: str) -> list:
    try:
        result = await asyncio.to_thread(
            client.models.embed_content,
            model="gemini-embedding-2",
            contents=text,
            config={"output_dimensionality": 768}
        )

        if hasattr(result, 'embeddings') and result.embeddings:
            return result.embeddings[0].values
        elif hasattr(result, 'embedding') and result.embedding:
            return result.embedding.values
        else:
            print(f"⚠️ Unexpected Response Structure: {dir(result)}")
            return None

    except Exception as e:
        print(f"❌ Embedding Generation Error: {e}")
        return None