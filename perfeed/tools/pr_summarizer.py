import asyncio
import json

import requests
from jinja2 import Environment, StrictUndefined

from perfeed.config_loader import settings
from perfeed.git_providers.base import BaseGitProvider
from perfeed.git_providers.github import GithubProvider
from perfeed.llms.base_client import BaseClient
from perfeed.models.pr_summary import PRSummary, PRSummaryMetadata
from perfeed.utils import json_output_curator
from datetime import datetime, timezone
from typing import Tuple


class PRSummarizer:
    def __init__(self, git: BaseGitProvider, llm: BaseClient):
        self.git = git
        self.llm = llm

    async def run(
        self, repo: str, pr_number: int
    ) -> Tuple[PRSummary, PRSummaryMetadata]:
        pr = await self.git.get_pr(repo, pr_number)

        self.variables = {
            "author": pr.author,
            "title": pr.title,
            "description": pr.description,
            "code": requests.get(pr.diff_url).text,
            "comments": pr.to_dict()["comments"],
            "PRSummary": PRSummary.to_json_schema(),
        }

        environment = Environment(undefined=StrictUndefined)
        system_prompt = environment.from_string(
            settings.pr_summary_prompt.system
        ).render(self.variables)
        user_prompt = environment.from_string(settings.pr_summary_prompt.user).render(
            self.variables
        )

        summary = self.llm.chat_completion(system_prompt, user_prompt)
        curated_summary = json_output_curator(summary)
        pr_summary = PRSummary(**json.loads(curated_summary))
        current_time = datetime.now(timezone.utc)
        pr_metadata = PRSummaryMetadata(
            repo=repo,
            author=pr.author,
            pr_number=pr_number,
            llm_provider=self.llm.__class__.__name__,
            model=self.llm.model,
            pr_created_at=pr.created_at,
            pr_merged_at=pr.merged_at,
            created_at=current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        return pr_summary, pr_metadata


if __name__ == "__main__":
    from perfeed.llms.ollama_client import OllamaClient
    from perfeed.llms.openai_client import OpenAIClient

    summarizer = PRSummarizer(
        GithubProvider("Perfeed"), llm=OllamaClient("llama3.1:8b")
    )
    # summarizer = PRSummarizer(GithubProvider("Perfeed"), llm=OpenAIClient("gpt-4o-mini"))
    pr_summary = asyncio.run(summarizer.run("perfeed", 13))
    print(pr_summary)
