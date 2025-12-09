"""Base platform provider implementation."""

import logging
from abc import ABC, abstractmethod

from auto_pr.platforms.models import CheckInfo, PRInfo, ReviewInfo
from auto_pr.platforms.protocol import PlatformProtocol

logger = logging.getLogger(__name__)


class BasePlatformProvider(ABC, PlatformProtocol):
    """Base class for platform providers.

    Provides common functionality and defines the interface that
    all platform providers must implement.
    """

    def __init__(self) -> None:
        self._repo_info: dict[str, str] | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the platform is available."""
        ...

    @abstractmethod
    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
        reviewers: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> PRInfo:
        """Create a new PR."""
        ...

    @abstractmethod
    def get_pr(self, pr_number: int) -> PRInfo:
        """Get PR information."""
        ...

    @abstractmethod
    def update_pr(
        self,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        draft: bool | None = None,
    ) -> PRInfo:
        """Update a PR."""
        ...

    @abstractmethod
    def close_pr(self, pr_number: int) -> None:
        """Close a PR."""
        ...

    @abstractmethod
    def merge_pr(
        self,
        pr_number: int,
        method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
        delete_branch: bool = False,
    ) -> bool:
        """Merge a PR."""
        ...

    @abstractmethod
    def can_merge(self, pr_number: int) -> tuple[bool, list[str]]:
        """Check if PR can be merged."""
        ...

    @abstractmethod
    def get_checks(self, pr_number: int) -> list[CheckInfo]:
        """Get PR checks."""
        ...

    @abstractmethod
    def get_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Get PR reviews."""
        ...

    @abstractmethod
    def request_reviewers(self, pr_number: int, reviewers: list[str]) -> None:
        """Request reviewers."""
        ...

    @abstractmethod
    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        """Add labels to PR."""
        ...

    @abstractmethod
    def get_default_branch(self) -> str:
        """Get default branch."""
        ...

    @abstractmethod
    def get_repo_info(self) -> dict[str, str]:
        """Get repository info."""
        ...

    @abstractmethod
    def list_prs(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        limit: int = 30,
    ) -> list[PRInfo]:
        """List PRs."""
        ...

    def find_pr_for_branch(self, branch: str, base: str | None = None) -> PRInfo | None:
        """Find an open PR for a given branch.

        Args:
            branch: Head branch to search for
            base: Base branch filter (optional)

        Returns:
            PRInfo if found, None otherwise
        """
        prs = self.list_prs(state="open", head=branch, base=base, limit=1)
        return prs[0] if prs else None

    def wait_for_checks(
        self,
        pr_number: int,
        timeout: int = 600,
        poll_interval: int = 30,
    ) -> tuple[bool, list[CheckInfo]]:
        """Wait for PR checks to complete.

        Default implementation polls get_checks(). Subclasses may override
        with more efficient implementations.

        Args:
            pr_number: PR number
            timeout: Maximum wait time in seconds
            poll_interval: Time between polls in seconds

        Returns:
            Tuple of (all_passed, list of checks)
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            checks = self.get_checks(pr_number)

            if not checks:
                return True, []

            pending = [c for c in checks if c.is_pending]
            if not pending:
                failed = [c for c in checks if c.is_failed]
                return len(failed) == 0, checks

            logger.debug(f"Waiting for {len(pending)} checks... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(poll_interval)

        return False, self.get_checks(pr_number)
