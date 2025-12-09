"""Review management for PR workflows."""

import logging
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from auto_pr.platforms.errors import ReviewRequiredError
from auto_pr.platforms.models import ReviewInfo, ReviewState
from auto_pr.platforms.protocol import PlatformProtocol

logger = logging.getLogger(__name__)


@dataclass
class ReviewSummary:
    """Summary of review status."""

    total: int
    approved: int
    changes_requested: int
    commented: int
    pending: int
    dismissed: int

    @property
    def is_approved(self) -> bool:
        return self.approved > 0 and self.changes_requested == 0

    @property
    def needs_changes(self) -> bool:
        return self.changes_requested > 0


class ReviewManager:
    """Manages review requests and status for PRs."""

    def __init__(
        self,
        platform: PlatformProtocol,
        console: Console | None = None,
    ) -> None:
        self.platform = platform
        self.console = console or Console()

    def get_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """Get reviews for a PR."""
        return self.platform.get_reviews(pr_number)

    def summarize_reviews(self, reviews: list[ReviewInfo]) -> ReviewSummary:
        """Summarize review statuses.

        Args:
            reviews: List of reviews

        Returns:
            ReviewSummary
        """
        approved = sum(1 for r in reviews if r.state == ReviewState.APPROVED)
        changes_requested = sum(1 for r in reviews if r.state == ReviewState.CHANGES_REQUESTED)
        commented = sum(1 for r in reviews if r.state == ReviewState.COMMENTED)
        pending = sum(1 for r in reviews if r.state == ReviewState.PENDING)
        dismissed = sum(1 for r in reviews if r.state == ReviewState.DISMISSED)

        return ReviewSummary(
            total=len(reviews),
            approved=approved,
            changes_requested=changes_requested,
            commented=commented,
            pending=pending,
            dismissed=dismissed,
        )

    def display_reviews(self, reviews: list[ReviewInfo]) -> None:
        """Display review status in a table."""
        if not reviews:
            self.console.print("[yellow]No reviews yet[/yellow]")
            return

        table = Table(title="Reviews")
        table.add_column("Reviewer", style="cyan")
        table.add_column("Status", style="white")

        for review in reviews:
            if review.state == ReviewState.APPROVED:
                status_str = "[green]Approved[/green]"
            elif review.state == ReviewState.CHANGES_REQUESTED:
                status_str = "[red]Changes Requested[/red]"
            elif review.state == ReviewState.PENDING:
                status_str = "[yellow]Pending[/yellow]"
            elif review.state == ReviewState.DISMISSED:
                status_str = "[dim]Dismissed[/dim]"
            else:
                status_str = "Commented"

            table.add_row(review.user, status_str)

        self.console.print(table)

    def request_reviewers(self, pr_number: int, reviewers: list[str]) -> None:
        """Request reviewers for a PR.

        Args:
            pr_number: PR number
            reviewers: List of usernames
        """
        if not reviewers:
            return

        self.platform.request_reviewers(pr_number, reviewers)
        self.console.print(f"[green]Requested reviews from: {', '.join(reviewers)}[/green]")

    def check_approval_status(
        self,
        pr_number: int,
        required_approvals: int = 1,
    ) -> tuple[bool, str]:
        """Check if PR has required approvals.

        Args:
            pr_number: PR number
            required_approvals: Number of approvals required

        Returns:
            Tuple of (approved, status_message)
        """
        reviews = self.get_reviews(pr_number)
        summary = self.summarize_reviews(reviews)

        if summary.changes_requested > 0:
            requesters = [r.user for r in reviews if r.state == ReviewState.CHANGES_REQUESTED]
            return False, f"Changes requested by: {', '.join(requesters)}"

        if summary.approved >= required_approvals:
            return True, f"Approved by {summary.approved} reviewer(s)"

        needed = required_approvals - summary.approved
        return False, f"Need {needed} more approval(s)"

    def get_reviewers_with_changes_requested(self, pr_number: int) -> list[str]:
        """Get reviewers who requested changes.

        Args:
            pr_number: PR number

        Returns:
            List of usernames
        """
        reviews = self.get_reviews(pr_number)
        return [r.user for r in reviews if r.state == ReviewState.CHANGES_REQUESTED]

    def get_approving_reviewers(self, pr_number: int) -> list[str]:
        """Get reviewers who approved.

        Args:
            pr_number: PR number

        Returns:
            List of usernames
        """
        reviews = self.get_reviews(pr_number)
        return [r.user for r in reviews if r.state == ReviewState.APPROVED]

    def get_pending_reviewers(self, pr_number: int) -> list[str]:
        """Get reviewers with pending review.

        Args:
            pr_number: PR number

        Returns:
            List of usernames
        """
        reviews = self.get_reviews(pr_number)
        return [r.user for r in reviews if r.state == ReviewState.PENDING]

    def display_review_status(self, pr_number: int) -> None:
        """Display comprehensive review status.

        Args:
            pr_number: PR number
        """
        reviews = self.get_reviews(pr_number)
        summary = self.summarize_reviews(reviews)

        self.console.print("\n[bold]Review Status[/bold]")

        if summary.approved > 0:
            approvers = self.get_approving_reviewers(pr_number)
            self.console.print(f"  [green]Approved by: {', '.join(approvers)}[/green]")

        if summary.changes_requested > 0:
            requesters = self.get_reviewers_with_changes_requested(pr_number)
            self.console.print(f"  [red]Changes requested by: {', '.join(requesters)}[/red]")

        if summary.pending > 0:
            pending = self.get_pending_reviewers(pr_number)
            self.console.print(f"  [yellow]Waiting on: {', '.join(pending)}[/yellow]")

        if summary.total == 0:
            self.console.print("  [yellow]No reviews yet[/yellow]")


def ensure_pr_approved(
    platform: PlatformProtocol,
    pr_number: int,
    required_approvals: int = 1,
    console: Console | None = None,
) -> bool:
    """Ensure PR has required approvals.

    Args:
        platform: Platform provider
        pr_number: PR number
        required_approvals: Number of approvals required
        console: Console for output

    Returns:
        True if approved

    Raises:
        ReviewRequiredError: If not approved
    """
    console = console or Console()
    manager = ReviewManager(platform, console)

    approved, message = manager.check_approval_status(pr_number, required_approvals)

    if approved:
        console.print(f"[green]{message}[/green]")
        return True

    reviews = manager.get_reviews(pr_number)
    summary = manager.summarize_reviews(reviews)

    if summary.changes_requested > 0:
        requesters = manager.get_reviewers_with_changes_requested(pr_number)
        raise ReviewRequiredError(
            required=required_approvals,
            approved=summary.approved,
            pr_number=pr_number,
            changes_requested_by=requesters,
        )

    raise ReviewRequiredError(
        required=required_approvals,
        approved=summary.approved,
        pr_number=pr_number,
    )
