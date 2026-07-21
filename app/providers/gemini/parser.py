import json

from app.providers.gemini.utils import create_openai_chunk
from app.services.analytics_service import save_request_analytics
from app.services.cache_service import save_to_semantic_cache


class GeminiParser:

    async def parse(
        self,
        upstream_response,
        background_tasks,
        last_prompt,
        model_name,
        chunk_id,
        user_id,
        client_ip,
    ):
        full_text_buffer = ""
        usage_metadata = {}
        raw_buffer = ""

        async for chunk in upstream_response.aiter_bytes():

            try:
                raw_buffer += chunk.decode("utf-8")
            except Exception as e:
                print(f"⚠️ Chunk decode error: {e}")
                continue

            while "\r\n\r\n" in raw_buffer:

                event, raw_buffer = raw_buffer.split("\r\n\r\n", 1)
                event = event.strip()

                if not event.startswith("data:"):
                    continue

                json_str = event[len("data:"):].strip()

                if not json_str or json_str == "[DONE]":
                    continue

                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    continue

                if not isinstance(data, dict):
                    continue

                if "usageMetadata" in data:
                    usage_metadata = data["usageMetadata"]

                if "candidates" in data and data["candidates"]:

                    candidate = data["candidates"][0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])

                    if parts:
                        text_part = parts[0].get("text", "")

                        if text_part:
                            full_text_buffer += text_part

                            yield create_openai_chunk(
                                chunk_id,
                                model_name,
                                text_part,
                            ).encode("utf-8")

        yield create_openai_chunk(
            chunk_id,
            model_name,
            "",
            finish_reason="stop",
        ).encode("utf-8")

        yield b"data: [DONE]\n\n"

        # Save cache
        if full_text_buffer.strip():

            print(
                f"📝 [BUFFER ASSEMBLED] Length: {len(full_text_buffer)} characters."
            )

            background_tasks.add_task(
                save_to_semantic_cache,
                last_prompt,
                full_text_buffer,
            )

        # Token calculation
        total_tokens = usage_metadata.get("totalTokenCount", 0)
        prompt_tokens = usage_metadata.get("promptTokenCount", 0)
        completion_tokens = usage_metadata.get("candidatesTokenCount", 0)

        token_source = "gemini_actual"

        if total_tokens == 0:

            token_source = "estimated_fallback"

            prompt_tokens = prompt_tokens or (len(last_prompt) // 4)
            completion_tokens = completion_tokens or (
                len(full_text_buffer) // 4
            )

            total_tokens = prompt_tokens + completion_tokens

        print(
            f"📊 [TOKEN SOURCE: {token_source}] "
            f"Prompt: {prompt_tokens} | "
            f"Completion: {completion_tokens} | "
            f"Total: {total_tokens}"
        )

        background_tasks.add_task(
            save_request_analytics,
            user_id,
            client_ip,
            model_name,
            last_prompt,
            False,
            total_tokens,
            prompt_tokens,
            completion_tokens,
        )