from fastapi import HTTPException

from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.openai_provider import OpenAIProvider


class ModelRouter:

    def __init__(self):

        self.providers = {
            "gemini": GeminiProvider(),
            "gpt": OpenAIProvider(),
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