import requests
from jinja2 import Environment, StrictUndefined

from src.config_loader import settings
from src.github import provider
from src.llms.base_client import BaseClient
from src.llms.ollama_client import OllamaClient


class PRSummarizer:
    def __init__(self, owner: str, llm: BaseClient):
        self.git = provider.GithubProvider(owner=owner)
        self.llm = llm

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

        summary = self.llm.chat_completion(system_prompt, user_prompt)
        print(summary)


if __name__ == "__main__":
    summarizer = PRSummarizer(owner="Perfeed", llm=OllamaClient("llama3.1:8b"))
    summarizer.run("perfeed", 5)
