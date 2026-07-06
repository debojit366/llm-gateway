# app/api/v1/endpoints/chat.py
from fastapi import APIRouter, Request, HTTPException, status, Body, BackgroundTasks # <-- BackgroundTasks import kiya
from fastapi.responses import StreamingResponse
from app.core.config import settings
from typing import Dict, Any
from app.services.analytics_service import save_request_analytics
import httpx

router = APIRouter()

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
        
    if "temperature" in openai_body:
        gemini_payload["generationConfig"] = {"temperature": openai_body["temperature"]}

    return gemini_payload


@router.post("/completions")
async def proxy_gemini_completions(
    request: Request, 
    background_tasks: BackgroundTasks, 
    payload: Dict[str, Any] = Body(...)
):
   
    body = payload

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

        background_tasks.add_task(save_request_analytics, client_ip, model_name, last_prompt)

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