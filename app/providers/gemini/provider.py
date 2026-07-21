from app.providers.base_provider import BaseProvider
import uuid



from fastapi.responses import StreamingResponse

from app.providers.gemini.client import GeminiClient
from app.services.analytics_service import save_request_analytics
from app.services.cache_service import check_semantic_cache
from app.providers.gemini.translator import translate_to_gemini_format
from app.providers.gemini.utils import create_openai_chunk
from app.providers.gemini.parser import GeminiParser



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

        gemini_payload = translate_to_gemini_format(body)
        client = GeminiClient()
        upstream_response = await client.generate(
            http_client=request.app.state.http_client,
            model_name=model_name,
            payload=gemini_payload,
        )
        parser = GeminiParser()

        return StreamingResponse(
            parser.parse(
                upstream_response=upstream_response,
                background_tasks=background_tasks,
                last_prompt=last_prompt,
                model_name=model_name,
                chunk_id=chunk_id,
                user_id=user_id,
                client_ip=client_ip,
            ),
            status_code=upstream_response.status_code,
            media_type="text/event-stream",
        )