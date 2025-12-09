"""Data models for platform operations."""

from dataclasses import dataclass, field
from enum import Enum


class PRState(Enum):
    """Pull request states."""

    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"
    DRAFT = "draft"


class CheckStatus(Enum):
    """CI/CD check statuses."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CheckConclusion(Enum):
    """CI/CD check conclusions."""

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"
    PENDING = "pending"


class ReviewState(Enum):
    """Review states."""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    PENDING = "PENDING"
    DISMISSED = "DISMISSED"


class MergeableState(Enum):
    """PR mergeable states."""

    MERGEABLE = "mergeable"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    BEHIND = "behind"
    UNSTABLE = "unstable"
    CLEAN = "clean"
    DIRTY = "dirty"
    HAS_HOOKS = "has_hooks"


@dataclass
class CheckInfo:
    """Information about a CI/CD check."""

    name: str
    status: CheckStatus
    conclusion: CheckConclusion | None = None
    url: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    @property
    def is_pending(self) -> bool:
        return self.status != CheckStatus.COMPLETED

    @property
    def is_successful(self) -> bool:
        return self.conclusion == CheckConclusion.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.conclusion in (CheckConclusion.FAILURE, CheckConclusion.TIMED_OUT, CheckConclusion.CANCELLED)


@dataclass
class ReviewInfo:
    """Information about a PR review."""

    user: str
    state: ReviewState
    body: str | None = None
    submitted_at: str | None = None

    @property
    def is_approved(self) -> bool:
        return self.state == ReviewState.APPROVED

    @property
    def requests_changes(self) -> bool:
        return self.state == ReviewState.CHANGES_REQUESTED


@dataclass
class PRInfo:
    """Information about a pull request."""

    number: int
    title: str
    body: str
    state: PRState
    head_branch: str
    base_branch: str
    url: str
    html_url: str | None = None
    mergeable: bool | None = None
    mergeable_state: MergeableState | None = None
    draft: bool = False
    checks: list[CheckInfo] = field(default_factory=list)
    reviews: list[ReviewInfo] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    author: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def is_open(self) -> bool:
        return self.state == PRState.OPEN

    @property
    def is_merged(self) -> bool:
        return self.state == PRState.MERGED

    @property
    def is_draft(self) -> bool:
        return self.draft or self.state == PRState.DRAFT

    @property
    def has_conflicts(self) -> bool:
        return self.mergeable_state in (MergeableState.CONFLICTING, MergeableState.DIRTY)

    @property
    def checks_passed(self) -> bool:
        if not self.checks:
            return True
        return all(c.is_successful for c in self.checks if c.status == CheckStatus.COMPLETED)

    @property
    def checks_pending(self) -> bool:
        return any(c.is_pending for c in self.checks)

    @property
    def checks_failed(self) -> bool:
        return any(c.is_failed for c in self.checks)

    @property
    def is_approved(self) -> bool:
        if not self.reviews:
            return False
        approved = [r for r in self.reviews if r.is_approved]
        changes_requested = [r for r in self.reviews if r.requests_changes]
        return len(approved) > 0 and len(changes_requested) == 0

    @property
    def pending_reviewers(self) -> list[str]:
        return [r.user for r in self.reviews if r.state == ReviewState.PENDING]

    @property
    def can_merge(self) -> bool:
        return (
            self.is_open
            and not self.is_draft
            and self.mergeable is not False
            and not self.has_conflicts
            and self.checks_passed
            and not self.checks_pending
        )

    def get_blocking_reasons(self) -> list[str]:
        reasons = []
        if not self.is_open:
            reasons.append(f"PR is {self.state.value}")
        if self.is_draft:
            reasons.append("PR is a draft")
        if self.has_conflicts:
            reasons.append("PR has merge conflicts")
        if self.checks_pending:
            pending = [c.name for c in self.checks if c.is_pending]
            reasons.append(f"Checks pending: {', '.join(pending[:3])}")
        if self.checks_failed:
            failed = [c.name for c in self.checks if c.is_failed]
            reasons.append(f"Checks failed: {', '.join(failed[:3])}")
        changes_requested = [r.user for r in self.reviews if r.requests_changes]
        if changes_requested:
            reasons.append(f"Changes requested by: {', '.join(changes_requested)}")
        return reasons
