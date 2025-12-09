"""CI/CD check monitoring and handling."""

import logging
import time
from dataclasses import dataclass

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from auto_pr.git import run_git_command
from auto_pr.platforms.errors import ChecksFailedError, ChecksPendingError
from auto_pr.platforms.models import CheckConclusion, CheckInfo, CheckStatus
from auto_pr.platforms.protocol import PlatformProtocol

logger = logging.getLogger(__name__)


@dataclass
class CheckSummary:
    """Summary of check statuses."""

    total: int
    passed: int
    failed: int
    pending: int
    skipped: int

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.pending == 0

    @property
    def has_failures(self) -> bool:
        return self.failed > 0

    @property
    def is_complete(self) -> bool:
        return self.pending == 0


class CheckMonitor:
    """Monitors CI/CD checks for PRs."""

    FLAKY_PATTERNS = ["e2e", "integration", "visual", "flaky", "unstable"]

    def __init__(
        self,
        platform: PlatformProtocol,
        console: Console | None = None,
    ) -> None:
        self.platform = platform
        self.console = console or Console()

    def get_checks(self, pr_number: int) -> list[CheckInfo]:
        """Get current checks for a PR."""
        return self.platform.get_checks(pr_number)

    def summarize_checks(self, checks: list[CheckInfo]) -> CheckSummary:
        """Summarize check statuses.

        Args:
            checks: List of checks

        Returns:
            CheckSummary
        """
        passed = sum(1 for c in checks if c.conclusion == CheckConclusion.SUCCESS)
        failed = sum(1 for c in checks if c.is_failed)
        pending = sum(1 for c in checks if c.is_pending)
        skipped = sum(1 for c in checks if c.conclusion in (CheckConclusion.SKIPPED, CheckConclusion.NEUTRAL))

        return CheckSummary(
            total=len(checks),
            passed=passed,
            failed=failed,
            pending=pending,
            skipped=skipped,
        )

    def display_checks(self, checks: list[CheckInfo]) -> None:
        """Display check statuses in a table."""
        table = Table(title="CI/CD Checks")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Conclusion", style="white")

        for check in sorted(checks, key=lambda c: (c.is_pending, not c.is_failed, c.name)):
            if check.is_pending:
                status_str = "[yellow]Running[/yellow]"
            elif check.status == CheckStatus.COMPLETED:
                status_str = "[green]Complete[/green]"
            else:
                status_str = check.status.value

            if check.conclusion is None:
                conclusion_str = "[yellow]Pending[/yellow]"
            elif check.conclusion == CheckConclusion.SUCCESS:
                conclusion_str = "[green]Success[/green]"
            elif check.is_failed:
                conclusion_str = f"[red]{check.conclusion.value}[/red]"
            else:
                conclusion_str = check.conclusion.value

            table.add_row(check.name, status_str, conclusion_str)

        self.console.print(table)

    def wait_for_checks(
        self,
        pr_number: int,
        timeout: int = 600,
        poll_interval: int = 30,
        show_progress: bool = True,
    ) -> tuple[bool, list[CheckInfo]]:
        """Wait for all checks to complete.

        Args:
            pr_number: PR number
            timeout: Maximum wait time in seconds
            poll_interval: Time between polls
            show_progress: Show progress indicator

        Returns:
            Tuple of (all_passed, final_checks)
        """
        start_time = time.time()
        last_status = ""

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Waiting for checks...", total=None)

                while time.time() - start_time < timeout:
                    checks = self.get_checks(pr_number)
                    summary = self.summarize_checks(checks)

                    status = f"Checks: {summary.passed} passed, {summary.failed} failed, {summary.pending} pending"

                    if status != last_status:
                        progress.update(task, description=status)
                        last_status = status

                    if summary.is_complete:
                        progress.stop()
                        return summary.all_passed, checks

                    time.sleep(poll_interval)

                progress.stop()
        else:
            while time.time() - start_time < timeout:
                checks = self.get_checks(pr_number)
                summary = self.summarize_checks(checks)

                if summary.is_complete:
                    return summary.all_passed, checks

                time.sleep(poll_interval)

        checks = self.get_checks(pr_number)
        summary = self.summarize_checks(checks)

        if summary.pending > 0:
            self.console.print(f"[yellow]Timeout: {summary.pending} check(s) still pending[/yellow]")

        return summary.all_passed, checks

    def is_flaky(self, check: CheckInfo) -> bool:
        """Identify potentially flaky checks.

        Args:
            check: Check to evaluate

        Returns:
            True if check appears flaky
        """
        name_lower = check.name.lower()
        return any(pattern in name_lower for pattern in self.FLAKY_PATTERNS)

    def categorize_failures(self, checks: list[CheckInfo]) -> tuple[list[CheckInfo], list[CheckInfo]]:
        """Categorize failed checks as flaky vs blocking.

        Args:
            checks: List of checks

        Returns:
            Tuple of (flaky_failures, blocking_failures)
        """
        failed = [c for c in checks if c.is_failed]
        flaky = [c for c in failed if self.is_flaky(c)]
        blocking = [c for c in failed if c not in flaky]
        return flaky, blocking

    def handle_failed_checks(
        self,
        checks: list[CheckInfo],
        interactive: bool = True,
    ) -> str:
        """Handle failed checks with user interaction.

        Args:
            checks: List of checks
            interactive: Allow user interaction

        Returns:
            Action to take: 'retry', 'ignore', 'abort', 'wait'
        """
        failed = [c for c in checks if c.is_failed]
        if not failed:
            return "continue"

        flaky, blocking = self.categorize_failures(checks)

        self.console.print()
        self.console.print("[bold red]CI/CD checks failed[/bold red]")

        if blocking:
            self.console.print("\n[red]Blocking failures:[/red]")
            for check in blocking:
                url_str = f" ({check.url})" if check.url else ""
                conclusion_str = check.conclusion.value if check.conclusion else "unknown"
                self.console.print(f"  - {check.name}: {conclusion_str}{url_str}")

        if flaky:
            self.console.print("\n[yellow]Potentially flaky failures:[/yellow]")
            for check in flaky:
                url_str = f" ({check.url})" if check.url else ""
                conclusion_str = check.conclusion.value if check.conclusion else "unknown"
                self.console.print(f"  - {check.name}: {conclusion_str}{url_str}")

        if not interactive:
            return "abort"

        if blocking:
            self.console.print("\n[red]Blocking checks must be fixed before merging.[/red]")
            choice = click.prompt(
                "What would you like to do?",
                type=click.Choice(["abort", "retry", "wait"]),
                default="abort",
            )
        elif flaky:
            self.console.print("\n[yellow]Only flaky tests failed. Retry may help.[/yellow]")
            choice = click.prompt(
                "What would you like to do?",
                type=click.Choice(["retry", "ignore", "abort", "wait"]),
                default="retry",
            )
        else:
            choice = "abort"

        return str(choice)

    def retry_checks(self, pr_number: int) -> bool:
        """Retry checks by amending and force pushing.

        This triggers a re-run of CI by creating an empty commit amendment.

        Args:
            pr_number: PR number

        Returns:
            True if retry was triggered successfully
        """
        self.console.print("[cyan]Triggering check retry via force push...[/cyan]")

        try:
            run_git_command(
                ["commit", "--amend", "--no-edit", "--allow-empty"],
                silent=True,
            )
            run_git_command(["push", "--force-with-lease"])
            self.console.print("[green]Checks retriggered[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Failed to retrigger checks: {e}[/red]")
            return False


def wait_for_pr_checks(
    platform: PlatformProtocol,
    pr_number: int,
    timeout: int = 600,
    interactive: bool = True,
    console: Console | None = None,
) -> bool:
    """Wait for PR checks and handle failures.

    Args:
        platform: Platform provider
        pr_number: PR number
        timeout: Maximum wait time
        interactive: Allow user interaction
        console: Console for output

    Returns:
        True if checks passed or user chose to proceed

    Raises:
        ChecksFailedError: If checks failed and user aborted
        ChecksPendingError: If checks still pending after timeout
    """
    console = console or Console()
    monitor = CheckMonitor(platform, console)

    passed, checks = monitor.wait_for_checks(pr_number, timeout)

    if passed:
        console.print("[green]All checks passed![/green]")
        return True

    summary = monitor.summarize_checks(checks)

    if summary.pending > 0:
        pending_names = [c.name for c in checks if c.is_pending]
        raise ChecksPendingError(pending_names, pr_number)

    action = monitor.handle_failed_checks(checks, interactive)

    if action == "retry":
        if monitor.retry_checks(pr_number):
            console.print("[cyan]Waiting for retried checks...[/cyan]")
            return wait_for_pr_checks(platform, pr_number, timeout, interactive, console)
        raise ChecksFailedError([c.name for c in checks if c.is_failed], pr_number)

    elif action == "ignore":
        console.print("[yellow]Proceeding despite failed checks[/yellow]")
        return True

    elif action == "wait":
        console.print("[cyan]Waiting longer for checks...[/cyan]")
        return wait_for_pr_checks(platform, pr_number, timeout, interactive, console)

    else:
        failed_names = [c.name for c in checks if c.is_failed]
        raise ChecksFailedError(failed_names, pr_number)
