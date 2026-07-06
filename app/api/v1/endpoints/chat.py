from fastapi import APIRouter, Request, HTTPException, status, Body, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.core.config import settings
from typing import Dict, Any, List
from app.core.security import verify_api_key
from app.services.analytics_service import save_request_analytics
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

        client_ip = request.client.host if request.client else "unknown"
        openai_messages = body.get("messages", [])
        last_prompt = openai_messages[-1].get("content", "") if openai_messages else ""

        user_id = str(current_user["_id"])

        background_tasks.add_task(save_request_analytics, client_ip, model_name, last_prompt, user_id)

        return StreamingResponse(
            upstream_response.aiter_bytes(),
            status_code=upstream_response.status_code,
            headers={"Content-Type": "application/json"}
        )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gemini Server is unreachable: {exc}"
        )