import os
import sys
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from ghapi.all import GhApi, pages
from src.github.models import CommentType, PRComment, PullRequest, FileDiff

class GithubProvider:
    def __init__(self, owner: str, token: str | None = None):
        load_dotenv()
        self.api = GhApi(owner=owner, token=token or os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN'))
        self.owner = owner

    def _get_pr_comments(self, owner: str, repo_name: str, pr_number: int, comment_type: CommentType) -> list[PRComment]:
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
            comments = self.api.issues.list_comments(owner=owner, repo=repo_name, issue_number=pr_number)
        else:
            comments = self.api.pulls.list_review_comments(owner=owner, repo=repo_name, pull_number=pr_number)

        return [
            PRComment(
                id=comment['id'],
                type=comment_type,
                user=comment['user']['login'],
                user_type=comment['user']['type'],
                diff_hunk=comment.get('diff_hunk'),
                body=comment.get('body'),
                created_at=comment['created_at'],
                in_reply_to_id=comment.get('in_reply_to_id'),
                html_url=comment['html_url']
            )
            for comment in comments
        ]

    def list_pr_comments(self, repo_name: str, pr_number: int) -> list[PRComment]:
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
        issue_comments = self._get_pr_comments(self.owner, repo_name, pr_number, CommentType.ISSUE_COMMENT)
        review_comments = self._get_pr_comments(self.owner, repo_name, pr_number, CommentType.REVIEW_COMMENT)
        return sorted(issue_comments + review_comments, key=lambda x: x.created_at)
    
    def get_patch(self, pr_file: dict) -> str:
        """
        Retrieve the patch (changes) for a file in a pull request.

        Args:
            pr_file (dict): The file information dictionary from the GitHub API.

        Returns:
            str: The patch content or 'no changes' if not available.
        """
        return pr_file.get('patch', 'no changes')

    def _to_PullRequest(self, pr: dict) -> PullRequest:
        """
        Convert a GitHub pull request dictionary into a `PullRequest` dataclass.

        Args:
            pr (dict): The pull request data from the GitHub API.

        Returns:
            PullRequest: The `PullRequest` object containing detailed information about the PR.
        """
        pr_number = pr['number']
        owner = self.owner
        repo_name = pr['base']['repo']['name']

        pr_files = self.api.pulls.list_files(owner=self.owner, repo=repo_name, pull_number=pr_number)
        code_diff: list[FileDiff] = []
        for file in pr_files:
            code_diff.append(FileDiff(file['filename'], file['status'], self.get_patch(file)))

        commits = self.api.pulls.list_commits(owner=self.owner, repo=repo_name, pull_number=pr_number)
        first_commit = commits[0].get('commit')
        first_committed_at = first_commit.get('author').get('date')
        diff_lines = f'+{pr.get("additions")} -{pr.get("deletions")}'
        merged_at = pr.get('merged_at') if pr.get('merged_at') != 'null' else None

        pr_reviewers = set()
        reviews = self.api.pulls.list_reviews(owner=self.owner, repo=repo_name, pull_number=pr_number)
        for review in reviews:
            # skip the review from the author and bots
            if review['user']['login'] == pr['user']['login'] or review['user']['type'] == 'Bot':
                continue
            else:
                pr_reviewers.add(review['user']['login'])

        # Read all PR comments
        pr_comments = self.list_pr_comments(repo_name, pr_number)

        return PullRequest(
            number=pr_number,
            title=pr['title'],
            author=pr['user']['login'],
            state=pr['state'],
            reviewers=list(pr_reviewers),
            created_at=pr['created_at'],
            first_committed_at=first_committed_at,
            description=pr['body'],
            code_diff=code_diff,
            diff_url=pr['html_url'],
            comments=pr_comments,
            diff_lines=diff_lines,
            merged_at=merged_at,
        )

    def fetch_pr(self, repo: str, pr_number: int) -> PullRequest:
        """
        Fetch a pull request based on its number.

        Args:
            owner (str): The owner of the repository. Could be an author or an organization
            repo_name (str): The name of the repository.
            pr_number (int): The pull request number.
            username (str): The username of the author to match.

        Returns:
            PullRequest: The `PullRequest` object containing detailed information about the PR.
        """
        pr = self.api.pulls.get(repo, pr_number)
        return self._to_PullRequest(pr)

    def fetch_pr_numbers(self, owner: str, repo_name: str, start_date: datetime, end_date: datetime):
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
            prs = self.api.pulls.list(owner=owner, repo=repo_name, state="closed", sort="created", direction="desc", per_page=100, page=page)
            # Filter PRs for the date range within this page
            filtered_prs = [
                pr for pr in prs 
                if start_date <= datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ') <= end_date
            ]
            
            all_prs.extend(filtered_prs)

            if len(prs) < 100:  # If fewer than 100 PRs were returned, this is the last page
                break

            page += 1
        
        return all_prs
    
    def download_user_repo_prs(self, owner: str, usernames: list[str], start_date: datetime, end_date: datetime, output_folder: str):
        """
        Download and save pull requests for specified users across all repositories under an organization within a date range.

        Args:
            owner (str): The owner of the repository.
            usernames (list[str]): A list of usernames whose PRs should be downloaded.
            start_date (datetime): The start date for filtering PRs.
            end_date (datetime): The end date for filtering PRs.
            output_folder (str): The relative path to the folder where the JSON files will be saved.

        Side Effect:
            Pull requests for each specified user are saved as JSON files in the specified output folder.
            The files are named using the format: {username}_{repo_name}_prs.json.
        """
        repos = pages(self.api.repos.list_for_org, self.api.last_page(), owner).concat()
        # Create the folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        # Iterate over each repository
        for repo in repos:
            repo_name = repo.name
            print(f"Processing repository: {repo_name}")

            # Fetch all PRs for the repo
            prs = self.fetch_pr_numbers(owner=owner, repo_name=repo_name, start_date=start_date, end_date=end_date)

            # Filter and save PRs by username
            for username in usernames:
                user_prs = []
                for pr in prs:
                    if pr['user']['login'] != username:
                        continue
                    pullRequest = self._to_PullRequest(pr)
                    if pullRequest:
                        user_prs.append(pullRequest)

                if user_prs:
                    # Convert the PullRequest objects to dictionaries before dumping to JSON
                    pullRequests_dict = [pr.to_dict() for pr in user_prs]
                    file_name = f'{username}_{repo_name}_prs.json'
                    file_path = os.path.join(output_folder, file_name)
                    with open(file_path, "w") as save_file:
                        json.dump(pullRequests_dict, save_file, indent=6)
                    print(f'Saved PRs for {username} in {file_name}')                      

# if __name__ == '__main__':
#     git = GithubProvider(owner='run-llama', token=None)
#     pr = git.fetch_pr('llama_index', 16309)
#     print(pr)