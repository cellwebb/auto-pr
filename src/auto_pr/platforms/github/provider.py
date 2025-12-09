"""GitHub platform provider with hybrid CLI/API approach."""

import logging

from auto_pr.platforms.base import BasePlatformProvider
from auto_pr.platforms.github.api_adapter import GitHubAPIAdapter
from auto_pr.platforms.github.cli_adapter import GitHubCLIAdapter
from auto_pr.platforms.models import CheckInfo, PRInfo, ReviewInfo
from auto_pr.platforms.registry import register_platform

logger = logging.getLogger(__name__)


@register_platform("github")
class GitHubProvider(BasePlatformProvider):
    """GitHub platform provider using gh CLI with API fallback.

    Prefers gh CLI for operations when available as it handles authentication
    seamlessly. Falls back to direct API calls when CLI is not installed.
    """

    def __init__(self) -> None:
        super().__init__()
        self._cli_adapter: GitHubCLIAdapter | None = None
        self._api_adapter: GitHubAPIAdapter | None = None

    @property
    def name(self) -> str:
        return "github"

    @property
    def cli_adapter(self) -> GitHubCLIAdapter:
        """Lazy-initialize CLI adapter."""
        if self._cli_adapter is None:
            self._cli_adapter = GitHubCLIAdapter()
        return self._cli_adapter

    @property
    def api_adapter(self) -> GitHubAPIAdapter:
        """Lazy-initialize API adapter."""
        if self._api_adapter is None:
            self._api_adapter = GitHubAPIAdapter()
        return self._api_adapter

    def _use_cli(self) -> bool:
        """Determine whether to use CLI or API."""
        return self.cli_adapter.is_available()

    def is_available(self) -> bool:
        """Check if either CLI or API is available."""
        cli_available = self.cli_adapter.is_available()
        api_available = self.api_adapter.is_available()

        if cli_available:
            logger.debug("Using GitHub CLI (gh)")
        elif api_available:
            logger.debug("Using GitHub API (GITHUB_TOKEN)")

        return cli_available or api_available

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
        if self._use_cli():
            return self.cli_adapter.create_pr(title, body, head, base, draft, reviewers, labels)
        return self.api_adapter.create_pr(title, body, head, base, draft, reviewers, labels)

    def get_pr(self, pr_number: int) -> PRInfo:
        """Get PR information."""
        if self._use_cli():
            return self.cli_adapter.get_pr(pr_number)
        return self.api_adapter.get_pr(pr_number)

    def update_pr(
        self,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        draft: bool | None = None,
    ) -> PRInfo:
        """Update a PR."""
        if self._use_cli():
            return self.cli_adapter.update_pr(pr_number, title, body, state, draft)
        return self.api_adapter.update_pr(pr_number, title, body, state, draft)

    def close_pr(self, pr_number: int) -> None:
        """Close a PR."""
        if self._use_cli():
            self.cli_adapter.close_pr(pr_number)
        else:
            self.api_adapter.close_pr(pr_number)

    def merge_pr(
        self,
        pr_number: int,
        method: str = "merge",
        commit_title: str | None = None,
        commit_message: str | None = None,
        delete_branch: bool = False,
    ) -> bool:
        """Merge a PR."""
        if self._use_cli():
            return self.cli_adapter.merge_pr(pr_number, method, commit_title, commit_message, delete_branch)
        return self.api_adapter.merge_pr(pr_number, method, commit_title, commit_message, delete_branch)

    def can_merge(self, pr_number: int) -> tuple[bool, list[str]]:
        """Check if PR can be merged."""
        if self._use_cli():
            return self.cli_adapter.can_merge(pr_number)
        return self.api_adapter.can_merge(pr_number)

    def get_checks(self, pr_number: int) -> list[CheckInfo]:
        """Get PR checks."""
        if self._use_cli():
            return self.cli_adapter.get_checks(pr_number)
        return self.api_adapter.get_checks(pr_number)

    def get_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Get PR reviews."""
        if self._use_cli():
            return self.cli_adapter.get_reviews(pr_number)
        return self.api_adapter.get_reviews(pr_number)

    def request_reviewers(self, pr_number: int, reviewers: list[str]) -> None:
        """Request reviewers."""
        if self._use_cli():
            self.cli_adapter.request_reviewers(pr_number, reviewers)
        else:
            self.api_adapter.request_reviewers(pr_number, reviewers)

    def add_labels(self, pr_number: int, labels: list[str]) -> None:
        """Add labels to PR."""
        if self._use_cli():
            self.cli_adapter.add_labels(pr_number, labels)
        else:
            self.api_adapter.add_labels(pr_number, labels)

    def get_default_branch(self) -> str:
        """Get default branch."""
        if self._use_cli():
            return self.cli_adapter.get_default_branch()
        return self.api_adapter.get_default_branch()

    def get_repo_info(self) -> dict[str, str]:
        """Get repository info."""
        if self._use_cli():
            return self.cli_adapter.get_repo_info()
        return self.api_adapter.get_repo_info()

    def list_prs(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        limit: int = 30,
    ) -> list[PRInfo]:
        """List PRs."""
        if self._use_cli():
            return self.cli_adapter.list_prs(state, head, base, limit)
        return self.api_adapter.list_prs(state, head, base, limit)
