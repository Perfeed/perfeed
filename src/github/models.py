from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommentType(Enum):
    ISSUE_COMMENT = 'issue_comment'
    REVIEW_COMMENT = 'review_comment'

@dataclass
class FileDiff:
    filename: str
    status: str
    patch: str

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "status": self.status,
            "patch": self.patch,
        }

@dataclass
class PRComment:
    id: int
    type: CommentType
    user: str
    user_type: str
    diff_hunk: Optional[str]
    body: Optional[str]
    created_at: str
    in_reply_to_id: Optional[int] = None
    html_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "user": self.user,
            "user_type": self.user_type,
            "diff_hunk": self.diff_hunk,
            "body": self.body,
            "created_at": self.created_at,
            "in_reply_to_id": self.in_reply_to_id,
            "html_url": self.html_url
        }

@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    author: str
    reviewers: list[str]
    created_at: str
    first_committed_at: str
    description: str
    code_diff: list[FileDiff]
    html_url: str
    diff_url: str
    comments: list[PRComment]
    diff_lines: str
    merged_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "author": self.author,
            "reviewers": self.reviewers,
            "created_at": self.created_at,
            "first_committed_at": self.first_committed_at,
            "description": self.description,
            "code_diff": [file_diff.to_dict() for file_diff in self.code_diff],
            "diff_url": self.diff_url,
            "html_url": self.html_url,
            "comments": [comment.to_dict() for comment in self.comments],
            "diff_lines": self.diff_lines,
            "merged_at": self.merged_at
        }
