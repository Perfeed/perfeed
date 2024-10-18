from typing import Any, Dict

import ollama

from .base_client import BaseClient


class OllamaClient(BaseClient):
    def __init__(self, model: str):
        self.model = model
        super().__init__()

    def chat_completion(self, system: str, user: str, **kwargs) -> str:
        """
        Generate a chat completion response using the specified model.

        This function interacts with the Ollama API to generate a response
        based on input messages from the system and the user. Additional
        parameters can be customized via kwargs.

        Args:
            system (str): The content of the message from the system.
            user (str): The content of the message from the user.
            **kwargs: Optional keyword arguments for additional options:
                - num_ctx (int): The context size for the model, default is 4096.
                - temperature (float): The randomness in the model's output,
                  default is 0.

        Returns:
            str: The content of the generated message response.
        """

        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options={
                "num_ctx": kwargs.get("num_ctx", 4096 * 2),
                "temperature": kwargs.get("temperature", 0),
            },
        )

        return response["message"]["content"]
