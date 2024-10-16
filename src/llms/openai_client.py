import os

from openai import OpenAI
from requests.exceptions import RequestException

from .base_client import BaseClient


class OpenAIClient(BaseClient):

    def __init__(self):
        super().__init__()

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("'OPENAI_API_KEY' not found via os.getenv")
        self.client = OpenAI(api_key=key)

    def chat_completion(
        self, model: str, system: str, user: str, parameters: dict
    ) -> str:
        try:
            temperature = parameters.get("temperature", 0.2)

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
        except RequestException as e:
            raise RuntimeError(f"Failed to communicate with the LLM platform: {str(e)}")

        return response.choices[0].message.content  # type: ignore
