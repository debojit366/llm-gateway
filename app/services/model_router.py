from fastapi import HTTPException

from app.providers.gemini.provider import GeminiProvider
from app.providers.groq.provider import GroqProvider

GROQ_MODELS = {"llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"}
class ModelRouter:

    def __init__(self):

        self.providers = {
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            
        }

    async def chat(
        self,
        request,
        payload,
        background_tasks,
        current_user,
    ):

        model = payload.model.lower()

        if model.startswith("gemini"):
            provider = self.providers["gemini"]

        elif model in GROQ_MODELS:
            provider = self.providers["groq"]

        elif model.startswith("gpt"):
            provider = self.providers["gpt"]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model {model}"
            )

        return await provider.chat(
            request=request,
            payload=payload,
            background_tasks=background_tasks,
            current_user=current_user,
        )


model_router = ModelRouter()