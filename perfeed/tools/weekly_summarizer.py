import asyncio
import time
from datetime import datetime, timedelta
from jinja2 import Environment, StrictUndefined
from perfeed.config_loader import settings
from perfeed.git_providers.base import BaseGitProvider
from perfeed.git_providers.github import GithubProvider
from perfeed.llms.base_client import BaseClient
from perfeed.llms.ollama_client import OllamaClient
from perfeed.log import get_logger
from perfeed.models.pr_summary import PRSummary
from perfeed.tools.pr_summarizer import PRSummarizer
from IPython.display import display, Markdown


class WeeklySummarizer:
    def __init__(self, git: BaseGitProvider, summarizer: PRSummarizer, llm: BaseClient):
        self.git = git
        self.summarizer = summarizer
        self.llm = llm

    async def run(self, users: list[str], repo_name: str, start_of_week: str) -> None:

        # Check if start_of_week must be the Sunday or Monday of the week
        try:
            date = datetime.strptime(start_of_week, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date format. Please use 'YYYY-MM-DD'.")

        # Check if the day of the week is Monday (0) or Sunday (-1)
        if date.weekday() not in [0, 6]:
            raise ValueError("Start day must be a Sunday or Monday.")

        # Use local timezone by default
        start_date = date.astimezone()
        end_date = start_date + timedelta(days=6)

        get_logger().info(
            f"Summarizing {repo_name} for {users} from {start_date} to {end_date}"
        )

        now = time.perf_counter()

        pr_numbers = await self.git.search_prs(
            repo_name, start_date, end_date, set(users), closed_only=True
        )
        # to ensure pr number can be found. if not, double check user id and date
        assert any(pr_numbers), "no pr number found."
        get_logger().info(f"Summarizing the following PR-{pr_numbers}")

        # TODO: load the PR summaries from the pervious batch if exists.

        summary_objects_futures = [
            self.summarizer.run(repo_name, pr_number) for pr_number in pr_numbers
        ]

        resolved_summaries = await asyncio.gather(
            *summary_objects_futures, return_exceptions=True
        )
        summaries = [resolved_summary[0] for resolved_summary in resolved_summaries if not isinstance(resolved_summary, BaseException)]

        elapsed = time.perf_counter() - now
        get_logger().info(f"Summarized {len(summaries)} PRs in {elapsed:0.5f} seconds")

        # TODO: store PRSummary results so we don't have to re-process again

        # TODO: handle failed summary futures with BaseException
        json_summaries = [
            summary.model_dump_json()
            for summary in summaries
            if not isinstance(summary, BaseException)
        ]
        self.variables = {
            "PRSummary": PRSummary.to_json_schema(),
            "pr_summaries": json_summaries,
        }

        environment = Environment(undefined=StrictUndefined)
        system_prompt = environment.from_string(
            settings.weekly_summary_prompt.system
        ).render(self.variables)
        user_prompt = environment.from_string(
            settings.weekly_summary_prompt.user
        ).render(self.variables)
        summary = self.llm.chat_completion(system_prompt, user_prompt)
        display(Markdown(summary))


if __name__ == "__main__":
    from perfeed.data_stores.storage_feather import FeatherStorage

    git = GithubProvider("Perfeed")
    llm = OllamaClient()
    store = FeatherStorage(data_type="pr_summary", overwrite=False, append=True)
    summarizer = PRSummarizer(
        git=git,
        llm=llm,
        store=store
    )
    weekly_summarizer = WeeklySummarizer(git=git, summarizer=summarizer, llm=llm)
    asyncio.run(
        weekly_summarizer.run(
            users=["jzxcd"],
            repo_name="perfeed",
            start_of_week="2024-10-21",
        )
    )
