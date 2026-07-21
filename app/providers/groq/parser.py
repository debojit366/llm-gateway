import json
from app.services.analytics_service import save_request_analytics
from app.services.cache_service import save_to_semantic_cache

class GroqParser:
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
        full_text = ""
        try:
            async for line in upstream_response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[len("data:"):].strip()

                if data_str == "[DONE]":
                    yield b"data: [DONE]\n\n"
                    break

                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0]["delta"]
                    content = delta.get("content", "")
                    if content:
                        full_text += content
                except (KeyError, IndexError, json.JSONDecodeError):
                    pass

                yield f"data: {data_str}\n\n".encode("utf-8")
        finally:
            await upstream_response.aclose()
            if full_text:
                background_tasks.add_task(save_to_semantic_cache, last_prompt, full_text)
            background_tasks.add_task(
                save_request_analytics,
                user_id, client_ip, model_name, last_prompt, False, len(full_text) // 4
            )