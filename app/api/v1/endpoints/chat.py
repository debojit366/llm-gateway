from fastapi import APIRouter, Request, Body, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import List
from app.core.security import verify_api_key
from app.services.model_router import model_router


router = APIRouter()

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message author")
    content: str = Field(..., description="The contents of the message")

class OpenAICompletionRequest(BaseModel):
    model: str = Field("gemini-2.5-flash", description="The ID of the model to use")
    messages: List[ChatMessage] = Field(..., description="A list of messages comprising the conversation")
    temperature: float = Field(None, description="What sampling temperature to use")
    stream: bool = Field(True, description="Enable streaming response")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gemini-2.5-flash",
                "messages": [{"role": "user", "content": "write your message here"}],
                "temperature": 0.7
            }
        }

@router.post("/completions")
async def proxy_completions(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: OpenAICompletionRequest = Body(...),
    current_user: dict = Depends(verify_api_key),
):

    return await model_router.chat(
        request=request,
        payload=payload,
        background_tasks=background_tasks,
        current_user=current_user,
    )