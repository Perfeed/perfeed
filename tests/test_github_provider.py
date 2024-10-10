import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.github.models import CommentType, PRComment, PullRequest, FileDiff
from src.github.provider import GithubProvider  # Adjust the import to match your structure

class TestGithubProvider(unittest.TestCase):

    @patch('src.github.provider.GhApi')
    def setUp(self, MockGhApi):
        """
        Set up a mock GithubProvider instance before each test.
        """
        self.mock_api = MockGhApi.return_value
        self.github_provider = GithubProvider(owner="test_owner", token="fake_token")

    def test_get_pr_comments_issue_comment(self):
        """
        Test _get_pr_comments with issue comments.
        """
        self.mock_api.issues.list_comments.return_value = [
            {
                "id": 1,
                "user": {"login": "test_user", "type": "User"},
                "created_at": "2023-10-01T10:00:00Z",
                "body": "Test issue comment",
                "html_url": "http://example.com/comment/1"
            }
        ]
        
        comments = self.github_provider._get_pr_comments("test_owner", "test_repo", 1, CommentType.ISSUE_COMMENT)
        
        self.assertEqual(len(comments), 1)
        self.assertIsInstance(comments[0], PRComment)
        self.assertEqual(comments[0].body, "Test issue comment")

    def test_get_pr_comments_review_comment(self):
        """
        Test _get_pr_comments with review comments.
        """
        self.mock_api.pulls.list_review_comments.return_value = [
            {
                "id": 2,
                "user": {"login": "review_user", "type": "User"},
                "created_at": "2023-10-01T11:00:00Z",
                "body": "Test review comment",
                "html_url": "http://example.com/comment/2"
            }
        ]
        
        comments = self.github_provider._get_pr_comments("test_owner", "test_repo", 1, CommentType.REVIEW_COMMENT)
        
        self.assertEqual(len(comments), 1)
        self.assertIsInstance(comments[0], PRComment)
        self.assertEqual(comments[0].body, "Test review comment")

    def test_list_pr_comments(self):
        """
        Test list_pr_comments to ensure it combines and sorts issue and review comments.
        """
        self.mock_api.issues.list_comments.return_value = [
            {"id": 1, "user": {"login": "test_user", "type": "User"}, "created_at": "2023-10-01T10:00:00Z", "body": "Issue comment", "html_url": "http://example.com/comment/1"}
        ]
        self.mock_api.pulls.list_review_comments.return_value = [
            {"id": 2, "user": {"login": "review_user", "type": "User"}, "created_at": "2023-10-01T11:00:00Z", "body": "Review comment", "html_url": "http://example.com/comment/2"}
        ]
        
        comments = self.github_provider.list_pr_comments("test_repo", 1)
        
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].created_at, "2023-10-01T10:00:00Z")
        self.assertEqual(comments[1].created_at, "2023-10-01T11:00:00Z")

    def test_get_patch(self):
        """
        Test get_patch method to ensure it returns correct patch content.
        """
        pr_file = {"patch": "Test patch content"}
        patch = self.github_provider.get_patch(pr_file)
        self.assertEqual(patch, "Test patch content")

        # Test case where patch is not available
        pr_file_no_patch = {}
        patch_no_content = self.github_provider.get_patch(pr_file_no_patch)
        self.assertEqual(patch_no_content, "no changes")

    def test_fetch_pr(self):
        """
        Test fetch_pr method to ensure it fetches and converts PR data.
        """
        pr_data = {
            "number": 123,
            "title": "Test PR",
            "user": {"login": "author"},
            "state": "open",
            "created_at": "2023-10-01T10:00:00Z",
            "body": "This is a test pull request.",
            "html_url": "http://example.com/pr/123",
            "additions": 10,
            "deletions": 5,
            "merged_at": None
        }
        
        # Mock the API response for fetch_pr method
        self.mock_api.pulls.get.return_value = pr_data
        
        # Patch _to_PullRequest method within github_provider instance
        with patch.object(self.github_provider, '_to_PullRequest', return_value=PullRequest(
            number=123,
            title="Test PR",
            state="open",
            author="author",
            reviewers=["reviewer1"],
            created_at="2023-10-01T10:00:00Z",
            first_committed_at="2023-09-30T10:00:00Z",
            description="This is a test pull request.",
            code_diff=[],
            diff_url="http://example.com/pr/123",
            comments=[],
            diff_lines="+10 -5",
            merged_at=None,
        )) as mock_to_pull_request:
            pull_request = self.github_provider.fetch_pr("test_repo", 123)
            mock_to_pull_request.assert_called_once_with(pr_data)
    
    @patch('src.github.provider.GithubProvider._get_pr_comments')
    def test_to_PullRequest(self, mock_get_pr_comments):
        """
        Test _to_PullRequest method to ensure it converts PR data correctly.
        """
        pr_data = {
            "number": 123,
            "title": "Test PR",
            "user": {"login": "author"},
            "base": {"repo": {"name": "test_repo"}},
            "state": "open",
            "created_at": "2023-10-01T10:00:00Z",
            "body": "This is a test pull request.",
            "html_url": "http://example.com/pr/123",
            "additions": 10,
            "deletions": 5,
            "merged_at": None
        }
        
        self.mock_api.pulls.list_files.return_value = [
            {"filename": "file1.py", "status": "modified", "patch": "patch content"}
        ]
        self.mock_api.pulls.list_commits.return_value = [
            {"commit": {"author": {"date": "2023-09-30T10:00:00Z"}}}
        ]
        self.mock_api.pulls.list_reviews.return_value = [
            {"user": {"login": "reviewer1", "type": "User"}}
        ]
        mock_get_pr_comments.return_value = []
                
        pull_request = self.github_provider._to_PullRequest(pr_data)
        
        self.assertEqual(pull_request.title, "Test PR")
        self.assertEqual(pull_request.diff_lines, "+10 -5")
        self.assertEqual(pull_request.reviewers, ["reviewer1"])

if __name__ == "__main__":
    unittest.main()
