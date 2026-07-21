import asyncio
import logging
from fastapi import HTTPException

from app.providers.gemini.provider import GeminiProvider
from app.providers.groq.provider import GroqProvider

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
GEMINI_MODELS = {"gemini-2.5-flash"}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 422}  # user/auth errors - no retry

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

    def get_fallback_provider(self, provider_name: str):
        if provider_name == "gemini":
            return self.providers["groq"], "groq"
        return self.providers["gemini"], "gemini"

    def intelligent_route(self, payload):
        text_parts = []
        has_image_payload = False

        # Extract text & check structured payloads (e.g., multimodal image attachments)
        for msg in payload.messages:
            if msg.role == "user":
                if isinstance(msg.content, str):
                    text_parts.append(msg.content)
                elif isinstance(msg.content, list):
                    for item in msg.content:
                        if isinstance(item, dict):
                            if item.get("type") in ("image_url", "image"):
                                has_image_payload = True
                            elif item.get("type") == "text":
                                text_parts.append(item.get("text", ""))

        prompt = " ".join(text_parts).lower()

        required = {
            "vision": has_image_payload,
            "reasoning": False,
            "coding": False,
            "context": len(prompt),
        }

        # -------- Detect Vision Keywords --------
        vision_words = ["image", "picture", "photo", "diagram", "screenshot", "ocr"]
        if any(word in prompt for word in vision_words):
            required["vision"] = True

        # -------- Detect Coding Keywords --------
        coding_words = [
            "code", "python", "cpp", "c++", "java", "javascript",
            "fastapi", "sql", "redis", "mongodb", "docker", "bug",
            "leetcode", "algorithm"
        ]
        if any(word in prompt for word in coding_words):
            required["coding"] = True

        # -------- Detect Reasoning Keywords --------
        reasoning_words = [
            "compare", "analyze", "analysis", "architecture",
            "design", "why", "explain", "research", "summarize"
        ]
        if any(word in prompt for word in reasoning_words):
            required["reasoning"] = True

        best_provider = None
        best_score = -float("inf")

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
            if required["context"] > 10_000:
                if capability["max_context"] >= required["context"]:
                    score += 5
                else:
                    score -= 50

            # Speed Preference
            score += capability["speed"]

            if score > best_score:
                best_score = score
                best_provider = capability["provider"]

        logger.info(f"[ROUTER] Selected Provider: {best_provider}")

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
        # Save original model BEFORE intelligent routing mutates payload.model
        original_model = payload.model
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

        provider_name = (
            "gemini" if isinstance(provider, GeminiProvider) else "groq"
        )

        last_exception = None

        # --------------------------
        # 1. Retry Same Provider
        # --------------------------
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"[RETRY] Attempt {attempt + 1} using {provider_name}")
                return await provider.chat(
                    request=request,
                    payload=payload,
                    background_tasks=background_tasks,
                    current_user=current_user,
                )
            except HTTPException as e:
                if e.status_code in NON_RETRYABLE_STATUS_CODES:
                    raise  # Bad request / Auth failure — do not retry or failover

                last_exception = e
                logger.warning(f"[ERROR] {provider_name} attempt {attempt + 1} failed (HTTP {e.status_code}): {e.detail}")
            except Exception as e:
                last_exception = e
                logger.warning(f"[ERROR] {provider_name} attempt {attempt + 1} failed: {e}")

            # Wait before retrying
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)

        # --------------------------
        # 2. Failover to Backup Provider
        # --------------------------
        fallback_provider, fallback_name = self.get_fallback_provider(provider_name)

        logger.warning(f"[FAILOVER] Switching from {provider_name} -> {fallback_name}")

        if fallback_name == "gemini":
            payload.model = "gemini-2.5-flash"
        else:
            payload.model = "llama-3.3-70b-versatile"

        try:
            return await fallback_provider.chat(
                request=request,
                payload=payload,
                background_tasks=background_tasks,
                current_user=current_user,
            )
        except HTTPException as e:
            payload.model = original_model
            if e.status_code in NON_RETRYABLE_STATUS_CODES:
                raise
            logger.error(f"[FAILOVER ERROR] {fallback_name} also failed (HTTP {e.status_code}): {e.detail}")

            raise last_exception if last_exception else e
        except Exception as e:
            payload.model = original_model
            logger.error(f"[FAILOVER ERROR] {fallback_name} also failed: {e}")
            raise last_exception if last_exception else e


model_router = ModelRouter()