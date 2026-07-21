from app.services.providers.base_provider import BaseProvider


class OpenAIProvider(BaseProvider):

    async def chat(
        self,
        request,
        payload,
        background_tasks,
        current_user,
    ):

        pass