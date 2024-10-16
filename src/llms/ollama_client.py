import ollama

from .base_client import BaseClient


class OllamaClient(BaseClient):
    def __init__(self):
        super().__init__()

    def chat_completion(
        self, model: str, system: str, user: str, parameters: dict
    ) -> str:

        num_ctx = parameters.get("num_ctx", 4096)
        temperature = parameters.get("temperature", 0.2)

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options={"num_ctx": num_ctx, "temperature": temperature},
        )

        return response["message"]["content"]
