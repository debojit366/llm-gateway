from app.services.providers.base_provider import BaseProvider
import json
import time
import uuid
import httpx

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.services.analytics_service import save_request_analytics
from app.services.cache_service import (
    check_semantic_cache,
    save_to_semantic_cache,
)



def translate_to_gemini_format(openai_body: dict) -> dict:
    openai_messages = openai_body.get("messages", [])
    gemini_contents = []
    system_instruction = None

    for msg in openai_messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        else:
            gemini_role = "model" if role == "assistant" else "user"
            gemini_contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

    gemini_payload = {"contents": gemini_contents}
    if system_instruction:
        gemini_payload["systemInstruction"] = system_instruction
    if "temperature" in openai_body and openai_body["temperature"] is not None:
        gemini_payload["generationConfig"] = {"temperature": openai_body["temperature"]}

    return gemini_payload


def create_openai_chunk(chunk_id: str, model_name: str, text: str, finish_reason: str = None) -> str:
    chunk_data = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "delta": {"content": text} if text else {},
                "finish_reason": finish_reason
            }
        ]
    }
    return f"data: {json.dumps(chunk_data)}\n\n"

class GeminiProvider(BaseProvider):

    async def chat(
        self,
        request,
        payload,
        background_tasks,
        current_user,
    ):

        body = payload.model_dump(exclude_unset=True)
        model_name = body.get("model", "gemini-2.5-flash")
        openai_messages = body.get("messages", [])
        last_prompt = openai_messages[-1].get("content", "") if openai_messages else ""
        
        user_id = str(current_user["_id"])
        client_ip = request.client.host if request.client else "unknown"
        chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}" 

        # -------------------------------------------------------------
        # STEP 1: SEMANTIC CACHE LOOKUP
        # -------------------------------------------------------------
        if last_prompt:
            cached_text, score = await check_semantic_cache(last_prompt)
            if cached_text:
                async def cached_streamer():
                    yield create_openai_chunk(chunk_id, model_name, cached_text, finish_reason=None).encode("utf-8")
                    yield create_openai_chunk(chunk_id, model_name, "", finish_reason="stop").encode("utf-8")
                    yield b"data: [DONE]\n\n"

                background_tasks.add_task(
                    save_request_analytics, user_id, client_ip, f"{model_name}-cached", last_prompt, True, len(cached_text) // 4
                )
                print(f"⚡ [CACHE STREAMED - OPENAI COMPATIBLE] Match score: {score:.4f}")
                return StreamingResponse(cached_streamer(), media_type="text/event-stream")

        # -------------------------------------------------------------
        #  STEP 2: CACHE MISS -> HIT GEMINI UPSTREAM
        # -------------------------------------------------------------
        gemini_payload = translate_to_gemini_format(body)
        upstream_url = f"{settings.GEMINI_BASE_URL}/models/{model_name}:streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        try:
            client = request.app.state.http_client
            upstream_request = client.build_request(
                "POST", upstream_url, json=gemini_payload, headers=headers, timeout=60.0
            )
            upstream_response = await client.send(upstream_request, stream=True)

            if upstream_response.status_code != 200:
                await upstream_response.aread() 
                raise HTTPException(
                    status_code=upstream_response.status_code, 
                    detail=f"Gemini Upstream Error: {upstream_response.text}"
                )


            async def response_interceptor():
                full_text_buffer = ""
                usage_metadata = {}
                raw_buffer = ""

                async for chunk in upstream_response.aiter_bytes():
                    # print(f"🔍 RAW GEMINI CHUNK >>> {chunk!r}")
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
                            # print(f"📊 USAGE METADATA FOUND: {usage_metadata}")

                        if "candidates" in data and data["candidates"]:
                            candidate = data["candidates"][0]
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                text_part = parts[0].get("text", "")
                                if text_part:
                                    full_text_buffer += text_part
                                    openai_formatted_chunk = create_openai_chunk(chunk_id, model_name, text_part)
                                    yield openai_formatted_chunk.encode("utf-8")

                yield create_openai_chunk(chunk_id, model_name, "", finish_reason="stop").encode("utf-8")
                yield b"data: [DONE]\n\n"

                if full_text_buffer.strip():
                    print(f"📝 [BUFFER ASSEMBLED] Length: {len(full_text_buffer)} characters.")
                    background_tasks.add_task(save_to_semantic_cache, last_prompt, full_text_buffer)

                total_tokens = usage_metadata.get("totalTokenCount", 0)
                prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
                token_source = "gemini_actual"
                if total_tokens == 0:
                    token_source = "estimated_fallback"
                    prompt_tokens = prompt_tokens or (len(last_prompt) // 4)
                    completion_tokens = completion_tokens or (len(full_text_buffer) // 4)
                    total_tokens = prompt_tokens + completion_tokens
                print(f"📊 [TOKEN SOURCE: {token_source}] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}")
                background_tasks.add_task(
                    save_request_analytics,
                    user_id, client_ip, model_name, last_prompt, False,
                    total_tokens, prompt_tokens, completion_tokens
                )

            return StreamingResponse(
                response_interceptor(),
                status_code=upstream_response.status_code,
                media_type="text/event-stream" 
            )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Gemini Server is unreachable: {exc}"
            )