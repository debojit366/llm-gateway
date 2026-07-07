from fastapi import APIRouter, Request, HTTPException, status, Body, BackgroundTasks, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.core.config import settings
from typing import Dict, Any, List
from app.core.security import verify_api_key
from app.services.analytics_service import save_request_analytics
from app.services.cache_service import check_semantic_cache, save_to_semantic_cache
import json
import httpx



router = APIRouter()
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message author (e.g., system, user, assistant)")
    content: str = Field(..., description="The contents of the message")

class OpenAICompletionRequest(BaseModel):
    model: str = Field("gemini-2.5-flash", description="The ID of the model to use")
    messages: List[ChatMessage] = Field(..., description="A list of messages comprising the conversation so far")
    temperature: float = Field(None, description="What sampling temperature to use")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gemini-2.5-flash",
                "messages": [
                    {"role": "user", "content": "write your message here"}
                ],
                "temperature": 0.7
            }
        }


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


@router.post("/completions")
async def proxy_gemini_completions(
    request: Request, 
    background_tasks: BackgroundTasks,
    payload: OpenAICompletionRequest = Body(...),
    current_user: dict = Depends(verify_api_key)
):
    body = payload.model_dump(exclude_unset=True)
    model_name = body.get("model", "gemini-2.5-flash")
    openai_messages = body.get("messages", [])
    last_prompt = openai_messages[-1].get("content", "") if openai_messages else ""
    
    user_id = str(current_user["_id"])
    client_ip = request.client.host if request.client else "unknown"

    # -------------------------------------------------------------
    #  SEMANTIC CACHE LOOKUP
    # -------------------------------------------------------------
    if last_prompt:
        cached_text, score = await check_semantic_cache(last_prompt)
        if cached_text:
            async def cached_streamer():
                mock_response = {
                    "candidates": [{
                        "content": {"parts": [{"text": cached_text}]},
                        "finishReason": "STOP"
                    }]
                }
                yield f"{json.dumps(mock_response)}\n".encode("utf-8")
                
            background_tasks.add_task(
                save_request_analytics, user_id, client_ip, f"{model_name}-cached", last_prompt
            )
            print(f"⚡ [CACHE STREAMED] Served instantly with match score: {score:.4f}")
            return StreamingResponse(cached_streamer(), headers={"Content-Type": "application/json"})

    # -------------------------------------------------------------
    # CACHE MISS -> HIT GEMINI UPSTREAM
    # -------------------------------------------------------------
    gemini_payload = translate_to_gemini_format(body)
    upstream_url = f"{settings.GEMINI_BASE_URL}/models/{model_name}:streamGenerateContent?key={settings.GEMINI_API_KEY}"
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

        # Analytics for fresh hit
        background_tasks.add_task(
            save_request_analytics, user_id, client_ip, model_name, last_prompt
        )

        async def response_interceptor():
            full_text_buffer = ""
            async for chunk in upstream_response.aiter_bytes():
                yield chunk  
                
                try:
                    chunk_str = chunk.decode("utf-8").strip()
                    
                    for line in chunk_str.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                            
                        cleaned_line = line.lstrip(",[").rstrip(",]")
                        if not cleaned_line:
                            continue
                            
                        try:
                            data = json.loads(cleaned_line)
                            if "candidates" in data and data["candidates"]:
                                candidate = data["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    text_part = candidate["content"]["parts"][0].get("text", "")
                                    full_text_buffer += text_part
                        except json.JSONDecodeError:
                            if '"text":' in cleaned_line:
                                try:
                                    parts = cleaned_line.split('"text":')
                                    if len(parts) > 1:
                                        text_val = parts[1].split('"')[1]
                                        text_part = bytes(text_val, "utf-8").decode("unicode_escape")
                                        full_text_buffer += text_part
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"⚠️ Chunk Interceptor Parsing Warning: {e}")

            if full_text_buffer.strip():
                print(f"📝 [BUFFER ASSEMBLED] Length: {len(full_text_buffer)} characters.")
                background_tasks.add_task(save_to_semantic_cache, last_prompt, full_text_buffer)
            else:
                print("⚠️ [CACHE WARNING] Could not assemble full text buffer from stream chunks.")




        return StreamingResponse(
            response_interceptor(),
            status_code=upstream_response.status_code,
            headers={"Content-Type": "application/json"}
        )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini Server is unreachable: {exc}"
        )