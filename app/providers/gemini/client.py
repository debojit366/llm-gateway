import httpx

from fastapi import HTTPException, status

from app.core.config import settings


class GeminiClient:

    async def generate(
        self,
        http_client: httpx.AsyncClient,
        model_name: str,
        payload: dict,
    ):

        upstream_url = (
            f"{settings.GEMINI_BASE_URL}/models/"
            f"{model_name}:streamGenerateContent"
            f"?alt=sse&key={settings.GEMINI_API_KEY}"
        )

        headers = {
            "Content-Type": "application/json"
        }

        try:

            request = http_client.build_request(
                "POST",
                upstream_url,
                json=payload,
                headers=headers,
                timeout=60.0,
            )

            response = await http_client.send(
                request,
                stream=True,
            )

            if response.status_code != 200:
                await response.aread()

                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Gemini Upstream Error: {response.text}",
                )

            return response

        except httpx.RequestError as exc:

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Gemini Server is unreachable: {exc}",
            )