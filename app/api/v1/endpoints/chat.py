from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.config import settings
import httpx

router = APIRouter()

@router.post("/completions")
async def proxy_chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    upstream_url = f"{settings.OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        client = request.app.state.http_client
        
        upstream_request = client.build_request(
            "POST", upstream_url, json=body, headers=headers, timeout=60.0
        )
        upstream_response = await client.send(upstream_request, stream=True)

        if upstream_response.status_code != 200:
            await upstream_response.aread()
            raise HTTPException(
                status_code=upstream_response.status_code, 
                detail=f"Upstream LLM Provider Error: {upstream_response.text}"
            )

        return StreamingResponse(
            upstream_response.aiter_bytes(),
            status_code=upstream_response.status_code,
            headers=dict(upstream_response.headers)
        )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to reach upstream LLM gateway: {exc}"
        )