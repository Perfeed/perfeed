import unittest
from src.github.models import FileDiff, PRComment, CommentType, PullRequest

class TestFileDiff(unittest.TestCase):
    def test_to_dict(self):
        file_diff = FileDiff(filename="test_file.py", status="modified", patch="@@ -1,2 +1,2 @@")
        expected_dict = {
            "filename": "test_file.py",
            "status": "modified",
            "patch": "@@ -1,2 +1,2 @@"
        }
        self.assertEqual(file_diff.to_dict(), expected_dict)

class TestPRComment(unittest.TestCase):
    def test_to_dict(self):
        pr_comment = PRComment(
            id=123,
            type=CommentType.ISSUE_COMMENT,
            user="test_user",
            user_type="User",
            diff_hunk="@@ -1 +1 @@",
            body="This is a comment.",
            created_at="2023-10-01T10:00:00Z",
            in_reply_to_id=456,
            html_url="http://example.com/comment/123"
        )
        expected_dict = {
            "id": 123,
            "type": "issue_comment",
            "user": "test_user",
            "user_type": "User",
            "diff_hunk": "@@ -1 +1 @@",
            "body": "This is a comment.",
            "created_at": "2023-10-01T10:00:00Z",
            "in_reply_to_id": 456,
            "html_url": "http://example.com/comment/123"
        }
        self.assertEqual(pr_comment.to_dict(), expected_dict)

    def test_to_dict_no_optional_fields(self):
        pr_comment = PRComment(
            id=123,
            type=CommentType.ISSUE_COMMENT,
            user="test_user",
            user_type="User",
            diff_hunk=None,
            body=None,
            created_at="2023-10-01T10:00:00Z"
        )
        expected_dict = {
            "id": 123,
            "type": "issue_comment",
            "user": "test_user",
            "user_type": "User",
            "diff_hunk": None,
            "body": None,
            "created_at": "2023-10-01T10:00:00Z",
            "in_reply_to_id": None,
            "html_url": None
        }
        self.assertEqual(pr_comment.to_dict(), expected_dict)

class TestPullRequest(unittest.TestCase):
    def test_to_dict(self):
        file_diff = FileDiff(filename="test_file.py", status="modified", patch="@@ -1,2 +1,2 @@")
        pr_comment = PRComment(
            id=123,
            type=CommentType.ISSUE_COMMENT,
            user="test_user",
            user_type="User",
            diff_hunk="@@ -1 +1 @@",
            body="This is a comment.",
            created_at="2023-10-01T10:00:00Z"
        )
        pull_request = PullRequest(
            number=1,
            title="Fix issue",
            state="open",
            author="contributor",
            reviewers=["reviewer1", "reviewer2"],
            created_at="2023-09-30T12:00:00Z",
            first_committed_at="2023-09-29T15:00:00Z",
            description="This PR fixes an issue.",
            code_diff=[file_diff],
            diff_url="http://example.com/diff/1",
            html_url="http://example.com/pr/1",
            comments=[pr_comment],
            diff_lines="+10 -2",
            merged_at=None
        )
        expected_dict = {
            "number": 1,
            "title": "Fix issue",
            "state": "open",
            "author": "contributor",
            "reviewers": ["reviewer1", "reviewer2"],
            "created_at": "2023-09-30T12:00:00Z",
            "first_committed_at": "2023-09-29T15:00:00Z",
            "description": "This PR fixes an issue.",
            "code_diff": [file_diff.to_dict()],
            "diff_url": "http://example.com/diff/1",
            "html_url":  "http://example.com/pr/1",
            "comments": [pr_comment.to_dict()],
            "diff_lines": "+10 -2",
            "merged_at": None
        }
        self.assertEqual(pull_request.to_dict(), expected_dict)

if __name__ == "__main__":
    unittest.main()
