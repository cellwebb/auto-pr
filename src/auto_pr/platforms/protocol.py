"""Protocol definition for platform providers."""

from typing import Protocol, runtime_checkable

from auto_pr.platforms.models import CheckInfo, PRInfo, ReviewInfo


@runtime_checkable
class PlatformProtocol(Protocol):
    """Protocol defining the interface for Git platform providers.

    Implementations must provide methods for:
    - PR lifecycle (create, read, update, close)
    - Merge operations
    - Check/CI monitoring
    - Review management
    - Branch operations
    """

    @property
    def name(self) -> str:
        """Platform name (e.g., 'github', 'gitlab')."""
        ...

    def is_available(self) -> bool:
        """Check if the platform is available (CLI installed or API configured)."""
        ...

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
        """Create a new pull request.

        Args:
            title: PR title
            body: PR description body
            head: Head branch name
            base: Base branch name
            draft: Create as draft PR
            reviewers: List of reviewers to request
            labels: List of labels to apply

        Returns:
            PRInfo for the created PR
        """
        ...

    def get_pr(self, pr_number: int) -> PRInfo:
        """Get information about a PR.

        Args:
            pr_number: PR number

        Returns:
            PRInfo with current PR state
        """
        ...

    def update_pr(
        self,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        draft: bool | None = None,
    ) -> PRInfo:
        """Update a PR.

        Args:
            pr_number: PR number
            title: New title (optional)
            body: New body (optional)
            state: New state (optional)
            draft: Set draft status (optional)

        Returns:
            Updated PRInfo
        """
        ...

    def close_pr(self, pr_number: int) -> None:
        """Close a PR without merging.

        Args:
            pr_number: PR number
        """
        ...

    def merge_pr(
        self,
        pr_number: int,
        method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
        delete_branch: bool = False,
    ) -> bool:
        """Merge a PR.

        Args:
            pr_number: PR number
            method: Merge method ('merge', 'squash', 'rebase')
            commit_title: Custom commit title (for squash/merge)
            commit_message: Custom commit message body
            delete_branch: Delete head branch after merge

        Returns:
            True if merge succeeded
        """
        ...

    def can_merge(self, pr_number: int) -> tuple[bool, list[str]]:
        """Check if a PR can be merged.

        Args:
            pr_number: PR number

        Returns:
            Tuple of (can_merge, list of blocking reasons)
        """
        ...

    def get_checks(self, pr_number: int) -> list[CheckInfo]:
        """Get CI/CD checks for a PR.

        Args:
            pr_number: PR number

        Returns:
            List of check information
        """
        ...

    def get_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Get reviews for a PR.

        Args:
            pr_number: PR number

        Returns:
            List of review information
        """
        ...

    def request_reviewers(self, pr_number: int, reviewers: list[str]) -> None:
        """Request reviewers for a PR.

        Args:
            pr_number: PR number
            reviewers: List of usernames to request
        """
        ...

    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        """Add labels to a PR.

        Args:
            pr_number: PR number
            labels: List of labels to add
        """
        ...

    def get_default_branch(self) -> str:
        """Get the repository's default branch.

        Returns:
            Default branch name
        """
        ...

    def get_repo_info(self) -> dict[str, str]:
        """Get repository information.

        Returns:
            Dict with 'owner', 'repo', 'url' keys
        """
        ...

    def list_prs(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        limit: int = 30,
    ) -> list[PRInfo]:
        """List PRs matching criteria.

        Args:
            state: PR state filter ('open', 'closed', 'all')
            head: Filter by head branch
            base: Filter by base branch
            limit: Maximum number to return

        Returns:
            List of matching PRInfo
        """
        ...
