import requests
from jinja2 import Environment, StrictUndefined

from src.config_loader import settings
from src.github import provider
from src.utils.llm_endpoint import LLM


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
        system_prompt = environment.from_string(settings.pr_summary_prompt.system).render(self.variables)
        user_prompt = environment.from_string(settings.pr_summary_prompt.user).render(self.variables)

        summary = self.llm.invoke(user_prompt=user_prompt, system_prompt=system_prompt)
        print(summary)


if __name__ == "__main__":
    summarizer = PRSummarizer(platform="openai", model="gpt-4o", owner="Perfeed")
    summarizer.run("perfeed", 5)
