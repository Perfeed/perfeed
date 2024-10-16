import json

import requests
from jinja2 import Environment, StrictUndefined

from src.config_loader import settings
from src.github import provider
from src.utils.llm_endpoint import LLM
from src.utils.tokenizer import count_tokens


# TODO: refactor the model settings (platform, model) for llm initialization to another function to be passed in.
class PRSummarizer:
    def __init__(self, platform: str, model: str, owner: str):
        self.git = provider.GithubProvider(owner=owner)
        self.llm = LLM(platform=platform, model_name=model)

    def run(self, repo: str, pr_number: int):
        pr = self.git.fetch_pr(repo, pr_number)

        self.variables = {
            "author": pr.author,
            "title": pr.title,
            "description": pr.description,
            "code": requests.get(pr.diff_url).text,
            "comments": pr.to_dict()["comments"],
        }

        environment = Environment(undefined=StrictUndefined)
        system_prompt = environment.from_string(
            settings.pr_summary_prompt.system
        ).render(self.variables)
        user_prompt = environment.from_string(settings.pr_summary_prompt.user).render(
            self.variables
        )

        print(f"Token count: {count_tokens(system_prompt + user_prompt)}")

        # override to use raw http request over openai api
        data = {
            "model": "llama3.1:8b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"num_ctx": 8192, "top_k": 10, "top_p": 0.1},
        }

        response = requests.post(
            "http://localhost:11434/api/chat",
            headers={"Content-Type": "application/json"},
            json=data,
        )
        json_data = json.loads(response.text)
        print(json_data['message']['content'])

        # summary = self.llm.invoke(user_prompt=user_prompt, system_prompt=system_prompt)
        # print(summary)


if __name__ == "__main__":
    summarizer = PRSummarizer(platform="openai", model="gpt-4o-mini", owner="Perfeed")
    # summarizer = PRSummarizer(
        # platform="ollama", model="llama3.1:8b-instruct-q4_0", owner="Perfeed"
    # )
    # summarizer = PRSummarizer(platform="ollama", model="codellama:13b-instruct", owner="Perfeed")

    summarizer.run("perfeed", 5)
