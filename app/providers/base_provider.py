from abc import ABC, abstractmethod


class BaseProvider(ABC):

    @abstractmethod
    async def chat(
        self,
        request,
        payload,
        background_tasks,
        current_user,
    ):
        pass