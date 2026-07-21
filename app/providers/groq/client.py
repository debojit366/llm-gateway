import httpx
from app.core.config import settings

class GroqClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.GROQ_BASE_URL

    async def generate(self, http_client: httpx.AsyncClient, payload: dict):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = http_client.build_request(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response = await http_client.send(req, stream=True)
        return response