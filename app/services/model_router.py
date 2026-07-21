from fastapi import HTTPException

from app.providers.gemini.provider import GeminiProvider
from app.providers.groq.provider import GroqProvider


GEMINI_MODELS = {"gemini-2.5-flash"}

GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
}


MODEL_CAPABILITIES = {
    "gemini": {
        "provider": "gemini",
        "vision": True,
        "reasoning": 10,
        "coding": 8,
        "speed": 8,
        "max_context": 1_000_000,
    },
    "groq": {
        "provider": "groq",
        "vision": False,
        "reasoning": 8,
        "coding": 9,
        "speed": 10,
        "max_context": 128_000,
    },
}


class ModelRouter:

    def __init__(self):

        self.providers = {
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
        }

    def intelligent_route(self, payload):

        prompt = " ".join(
            msg.content
            for msg in payload.messages
            if msg.role == "user" and isinstance(msg.content, str)
        ).lower()

        required = {
            "vision": False,
            "reasoning": False,
            "coding": False,
            "context": len(prompt),
        }

        # -------- Detect Vision --------

        vision_words = [
            "image",
            "picture",
            "photo",
            "diagram",
            "screenshot",
            "ocr",
        ]

        if any(word in prompt for word in vision_words):
            required["vision"] = True

        # -------- Detect Coding --------

        coding_words = [
            "code",
            "python",
            "cpp",
            "c++",
            "java",
            "javascript",
            "fastapi",
            "sql",
            "redis",
            "mongodb",
            "docker",
            "bug",
            "leetcode",
            "algorithm",
        ]

        if any(word in prompt for word in coding_words):
            required["coding"] = True

        # -------- Detect Reasoning --------

        reasoning_words = [
            "compare",
            "analyze",
            "analysis",
            "architecture",
            "design",
            "why",
            "explain",
            "research",
            "summarize",
        ]

        if any(word in prompt for word in reasoning_words):
            required["reasoning"] = True

        best_provider = None
        best_score = -1

        for capability in MODEL_CAPABILITIES.values():

            score = 0

            # Vision
            if required["vision"]:
                if capability["vision"]:
                    score += 10
                else:
                    score -= 100

            # Coding
            if required["coding"]:
                score += capability["coding"]

            # Reasoning
            if required["reasoning"]:
                score += capability["reasoning"]

            # Long Context
            if required["context"] > 10000:
                if capability["max_context"] >= required["context"]:
                    score += 5
                else:
                    score -= 50

            # Default Preference
            score += capability["speed"]

            if score > best_score:
                best_score = score
                best_provider = capability["provider"]
        print(f"[ROUTER] Selected Provider: {best_provider}", flush=True)
        if best_provider == "gemini":
            payload.model = "gemini-2.5-flash"
        elif best_provider == "groq":
            payload.model = "llama-3.3-70b-versatile"
        return self.providers[best_provider]

    async def chat(
        self,
        request,
        payload,
        background_tasks,
        current_user,
    ):

        model = payload.model.lower()

        if model == "auto":
            provider = self.intelligent_route(payload)

        elif model in GEMINI_MODELS:
            provider = self.providers["gemini"]

        elif model in GROQ_MODELS:
            provider = self.providers["groq"]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model {model}",
            )

        return await provider.chat(
            request=request,
            payload=payload,
            background_tasks=background_tasks,
            current_user=current_user,
        )


model_router = ModelRouter()