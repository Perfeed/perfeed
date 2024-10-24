import asyncio
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from ghapi.all import GhApi

from perfeed.git_providers.base import BaseGitProvider
from perfeed.models.git_provider import CommentType, PRComment, PullRequest


class GithubProvider(BaseGitProvider):
    def __init__(self, owner: str, token: str | None = None):
        self.owner = owner

        load_dotenv()
        self.api = GhApi(
            owner=owner, token=token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        )

    async def _get_pr_comments(
        self, owner: str, repo_name: str, pr_number: int, comment_type: CommentType
    ) -> list[PRComment]:
        """
        Retrieves comments associated with a pull request, filtered by comment type.

        Args:
            owner (str): The owner of the repository.
            repo_name (str): The name of the repository.
            pr_number (int): The pull request number.
            comment_type (CommentType): The type of comments to retrieve (issue or review).

        Returns:
            list[PRComment]: A list of PRComment objects representing the comments of the specified type.
        """
        if comment_type == CommentType.ISSUE_COMMENT:
            comments = await asyncio.to_thread(
                self.api.issues.list_comments,  # type: ignore
                owner=owner,
                repo=repo_name,
                issue_number=pr_number,
            )
        else:
            comments = await asyncio.to_thread(
                self.api.pulls.list_review_comments,  # type: ignore
                owner=owner,
                repo=repo_name,
                pull_number=pr_number,
            )

        return [
            PRComment(
                id=comment["id"],
                type=comment_type,
                user=comment["user"]["login"],
                user_type=comment["user"]["type"],
                diff_hunk=comment.get("diff_hunk"),
                body=comment.get("body"),
                created_at=comment["created_at"],
                in_reply_to_id=comment.get("in_reply_to_id"),
                html_url=comment["html_url"],
            )
            for comment in comments
        ]

    async def list_pr_comments(self, repo_name: str, pr_number: int) -> list[PRComment]:
        """
        Lists all the comments associated with a GitHub pull request.

        This method retrieves both issue comments and review comments for the specified pull request number.
        It returns a list of `PRComment` objects, which contain the relevant details for each comment, such as the user, diff hunk, body, and creation timestamp.

        The comments are sorted by their creation timestamp in ascending order.

        Args:
            owner (str): The owner of the repository.
            repo_name (str): The name of the repository.
            pr_number (int): The number of the pull request to fetch comments for.

        Returns:
            list[PRComment]: A list of `PRComment` objects representing the comments for the specified pull request.
        """
        awaitable_issue_comments = self._get_pr_comments(
            self.owner, repo_name, pr_number, CommentType.ISSUE_COMMENT
        )
        awaitable_review_comments = self._get_pr_comments(
            self.owner, repo_name, pr_number, CommentType.REVIEW_COMMENT
        )
        comments = await asyncio.gather(
            awaitable_issue_comments, awaitable_review_comments
        )
        return sorted(comments[0] + comments[1], key=lambda x: x.created_at)

    async def _to_PullRequest(self, pr: dict) -> PullRequest:
        """
        Convert a GitHub pull request dictionary into a `PullRequest` dataclass.

        Args:
            pr (dict): The pull request data from the GitHub API.

        Returns:
            PullRequest: The `PullRequest` object containing detailed information about the PR.
        """
        pr_number = pr["number"]
        repo_name = pr["base"]["repo"]["name"]

        awaitable_commits = asyncio.to_thread(
            self.api.pulls.list_commits,  # type: ignore
            owner=self.owner,
            repo=repo_name,
            pull_number=pr_number,
        )
        awaitable_reviews = asyncio.to_thread(
            self.api.pulls.list_reviews,  # type: ignore
            owner=self.owner,
            repo=repo_name,
            pull_number=pr_number,
        )
        awaitable_comments = self.list_pr_comments(repo_name, pr_number)

        results = await asyncio.gather(
            awaitable_commits, awaitable_reviews, awaitable_comments
        )
        commits = results[0]
        reviews = results[1]
        comments = results[2]

        first_commit = commits[0].get("commit")
        first_committed_at = first_commit.get("author").get("date")
        diff_lines = f'+{pr.get("additions")} -{pr.get("deletions")}'
        merged_at = pr.get("merged_at") if pr.get("merged_at") != "null" else None

        pr_reviewers = set()
        for review in reviews:
            # skip the review from the author and bots
            if (
                review["user"]["login"] == pr["user"]["login"]
                or review["user"]["type"] == "Bot"
            ):
                continue
            else:
                pr_reviewers.add(review["user"]["login"])

        return PullRequest(
            number=pr_number,
            title=pr["title"],
            author=pr["user"]["login"],
            state=pr["state"],
            reviewers=list(pr_reviewers),
            created_at=pr["created_at"],
            first_committed_at=first_committed_at,
            description=pr["body"],
            html_url=pr["html_url"],
            diff_url=pr["diff_url"],
            comments=comments,
            diff_lines=diff_lines,
            merged_at=merged_at,
        )

    async def get_pr(self, repo: str, pr_number: int) -> PullRequest:
        """
        Fetch a pull request based on its number.

        Args:
            repo (str): The name of the repository.
            pr_number (int): The pull request number.

        Returns:
            PullRequest: The `PullRequest` object containing detailed information about the PR.
        """
        pr = await asyncio.to_thread(self.api.pulls.get, repo, pr_number)  # type: ignore
        return await self._to_PullRequest(pr)

    ## TODO: This method currently doesn't handle the situation where [start_date, end_date] is way in the past so the first page of 100 PRs won't be included and will just return prematurely.
    async def list_pr_numbers(
        self, owner: str, repo_name: str, start_date: datetime, end_date: datetime
    ) -> list[int]:
        """
        Fetch all pull request numbers within a specified date range.

        Args:
            owner (str): The owner of the repository. Could be an author or an organization
            repo_name (str): The name of the repository.
            start_date (datetime): The start date for filtering PRs.
            end_date (datetime): The end date for filtering PRs.

        Returns:
            list[dict]: A list of pull request dictionaries.
        """
        all_prs = []
        page = 1
        while True:
            prs = await asyncio.to_thread(self.api.pulls.list, owner=owner, repo=repo_name, state="closed", sort="created", direction="desc", per_page=100, page=page)  # type: ignore
            # Filter PRs for the date range within this page
            filtered_prs = [
                pr.number
                for pr in prs
                if start_date
                <= datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                <= end_date
            ]

            all_prs.extend(filtered_prs)

            # this is the last page that fits the filter condition
            if len(filtered_prs) < 100:
                break

            page += 1

        return all_prs


# if __name__ == "__main__":
#     import time

#     git = GithubProvider(owner="run-llama", token=None)

#     now = time.perf_counter()
#     pr = asyncio.run(git.get_pr("llama_index", 16309))
#     elapsed = time.perf_counter() - now
#     print(f"Took {elapsed:0.5f} seconds.\n{pr}")

#     print("===============================")

#     end = datetime.now()
#     start = end - timedelta(days=7)
#     now = time.perf_counter()
#     pr_numbers = asyncio.run(
#         git.list_pr_numbers("run-llama", "llama_index", start, end)
#     )
#     elapsed = time.perf_counter() - now
#     print(f"Took {elapsed:0.5f} seconds.\n {pr_numbers}")