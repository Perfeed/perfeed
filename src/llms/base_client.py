from abc import ABC, abstractmethod


class BaseClient(ABC):
    """
    This class defines the interface for a LLM client.
    """

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def chat_completion(
        self, model: str, system: str, user: str, parameters: dict
    ) -> str:
        """
        This method should be implemented to return a chat completion from the AI model.
        Args:
            model (str): the name of the model to use for the chat completion
            system (str): the system message string to use for the chat completion
            user (str): the user message string to use for the chat completion
            data (dict): the data to be used in the chat completion

        Returns: the chat completion response
        """
        pass
