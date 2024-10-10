import unittest
from unittest import mock

from src.utils.llm_endpoint import LLM


class TestLLM(unittest.TestCase):

    def test_platform_with_key(self):
        with mock.patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "dummy_key", "OPENROUTER_API_KEY": "dummy_key"},
        ):
            llm_openai = LLM(platform="openai", model_name="gpt-3")
            self.assertIsNotNone(llm_openai.client)

            llm_ollama = LLM(platform="ollama", model_name="llama3")
            self.assertIsNotNone(llm_openai.client)

            llm_openrouter = LLM(platform="openrouter", model_name="llama3")
            self.assertIsNotNone(llm_openai.client)

    def test_openai_platform_without_key(self):
        with self.assertRaises(RuntimeError) as context:
            LLM(platform="openai", model_name="gpt-3")
        self.assertIn(
            "'OPENAI_API_KEY' not found via os.getenv", str(context.exception)
        )

    def test_invalid_platform(self):
        with self.assertRaises(RuntimeError) as context:
            LLM(platform="invalid_platform", model_name="llama9")
        self.assertIn(
            'platform "invalid_platform" not recognized/supported.',
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
