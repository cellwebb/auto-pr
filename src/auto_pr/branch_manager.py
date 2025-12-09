"""Branch management operations for PR workflows."""

import logging
from typing import Any

import click
from rich.console import Console

from auto_pr.errors import GitError
from auto_pr.git import get_current_branch, run_git_command

logger = logging.getLogger(__name__)


class BranchManager:
    """Manages branch operations for PR workflows."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        return get_current_branch()

    def branch_exists(self, branch: str, remote: bool = False) -> bool:
        """Check if a branch exists.

        Args:
            branch: Branch name
            remote: Check remote instead of local

        Returns:
            True if branch exists
        """
        try:
            if remote:
                run_git_command(["ls-remote", "--heads", "origin", branch], silent=True)
            else:
                run_git_command(["rev-parse", "--verify", branch], silent=True)
            return True
        except GitError:
            return False

    def get_commits_behind(self, base_branch: str) -> int:
        """Get number of commits current branch is behind base.

        Args:
            base_branch: Base branch to compare against

        Returns:
            Number of commits behind
        """
        try:
            run_git_command(["fetch", "origin", base_branch], silent=True)
            output = run_git_command(
                ["rev-list", "--count", f"HEAD..origin/{base_branch}"],
                silent=True,
            )
            return int(output.strip())
        except (GitError, ValueError):
            return 0

    def get_commits_ahead(self, base_branch: str) -> int:
        """Get number of commits current branch is ahead of base.

        Args:
            base_branch: Base branch to compare against

        Returns:
            Number of commits ahead
        """
        try:
            run_git_command(["fetch", "origin", base_branch], silent=True)
            output = run_git_command(
                ["rev-list", "--count", f"origin/{base_branch}..HEAD"],
                silent=True,
            )
            return int(output.strip())
        except (GitError, ValueError):
            return 0

    def is_branch_pushed(self, branch: str | None = None) -> bool:
        """Check if branch is pushed to remote.

        Args:
            branch: Branch name (default: current)

        Returns:
            True if branch exists on remote
        """
        branch = branch or self.get_current_branch()
        return self.branch_exists(branch, remote=True)

    def is_up_to_date(self, base_branch: str) -> bool:
        """Check if current branch is up to date with base.

        Args:
            base_branch: Base branch to compare against

        Returns:
            True if up to date
        """
        return self.get_commits_behind(base_branch) == 0

    def sync_with_base(
        self,
        base_branch: str,
        strategy: str = "rebase",
        interactive: bool = True,
    ) -> bool:
        """Synchronize current branch with base branch.

        Args:
            base_branch: Base branch to sync with
            strategy: Sync strategy ('rebase' or 'merge')
            interactive: Prompt user on failure

        Returns:
            True if sync succeeded
        """
        behind = self.get_commits_behind(base_branch)

        if behind == 0:
            self.console.print(f"[green]Branch is up to date with {base_branch}[/green]")
            return True

        self.console.print(f"[yellow]Branch is {behind} commit(s) behind {base_branch}[/yellow]")

        if strategy == "rebase":
            return self._sync_rebase(base_branch, interactive)
        elif strategy == "merge":
            return self._sync_merge(base_branch, interactive)
        else:
            self.console.print(f"[red]Unknown sync strategy: {strategy}[/red]")
            return False

    def _sync_rebase(self, base_branch: str, interactive: bool) -> bool:
        """Sync via rebase."""
        self.console.print(f"[cyan]Rebasing onto {base_branch}...[/cyan]")

        try:
            run_git_command(["fetch", "origin", base_branch], silent=True)
            run_git_command(["rebase", f"origin/{base_branch}"])
            self.console.print("[green]Rebase successful[/green]")
            return True
        except GitError as e:
            self.console.print(f"[red]Rebase failed: {e}[/red]")

            if interactive:
                choice = click.prompt(
                    "What would you like to do?",
                    type=click.Choice(["abort", "continue_manual"]),
                    default="abort",
                )
                if choice == "abort":
                    try:
                        run_git_command(["rebase", "--abort"], silent=True)
                        self.console.print("[yellow]Rebase aborted[/yellow]")
                    except GitError:
                        pass
            return False

    def _sync_merge(self, base_branch: str, interactive: bool) -> bool:
        """Sync via merge."""
        self.console.print(f"[cyan]Merging {base_branch}...[/cyan]")

        try:
            run_git_command(["fetch", "origin", base_branch], silent=True)
            run_git_command(["merge", f"origin/{base_branch}"])
            self.console.print("[green]Merge successful[/green]")
            return True
        except GitError as e:
            self.console.print(f"[red]Merge failed: {e}[/red]")

            if interactive:
                choice = click.prompt(
                    "What would you like to do?",
                    type=click.Choice(["abort", "continue_manual"]),
                    default="abort",
                )
                if choice == "abort":
                    try:
                        run_git_command(["merge", "--abort"], silent=True)
                        self.console.print("[yellow]Merge aborted[/yellow]")
                    except GitError:
                        pass
            return False

    def push_branch(self, force: bool = False, set_upstream: bool = False) -> bool:
        """Push current branch to remote.

        Args:
            force: Use force push (with lease)
            set_upstream: Set upstream tracking

        Returns:
            True if push succeeded
        """
        args = ["push"]

        if force:
            args.append("--force-with-lease")

        if set_upstream:
            branch = self.get_current_branch()
            args.extend(["-u", "origin", branch])

        try:
            run_git_command(args)
            self.console.print("[green]Push successful[/green]")
            return True
        except GitError as e:
            self.console.print(f"[red]Push failed: {e}[/red]")

            if "rejected" in str(e).lower() and not force:
                self.console.print("[yellow]Tip: Use force push after rebasing[/yellow]")

            return False

    def force_push_safely(self) -> bool:
        """Force push with lease for safety.

        Returns:
            True if push succeeded
        """
        return self.push_branch(force=True)

    def delete_branch(self, branch: str, remote: bool = False) -> bool:
        """Delete a branch.

        Args:
            branch: Branch name
            remote: Delete from remote

        Returns:
            True if deletion succeeded
        """
        try:
            if remote:
                run_git_command(["push", "origin", "--delete", branch])
                self.console.print(f"[green]Deleted remote branch: {branch}[/green]")
            else:
                run_git_command(["branch", "-D", branch])
                self.console.print(f"[green]Deleted local branch: {branch}[/green]")
            return True
        except GitError as e:
            self.console.print(f"[red]Failed to delete branch {branch}: {e}[/red]")
            return False

    def checkout_branch(self, branch: str, create: bool = False) -> bool:
        """Checkout a branch.

        Args:
            branch: Branch name
            create: Create if doesn't exist

        Returns:
            True if checkout succeeded
        """
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)

        try:
            run_git_command(args)
            return True
        except GitError as e:
            self.console.print(f"[red]Failed to checkout {branch}: {e}[/red]")
            return False

    def ensure_branch_pushed(self, branch: str | None = None) -> bool:
        """Ensure branch is pushed to remote.

        Args:
            branch: Branch name (default: current)

        Returns:
            True if branch is pushed
        """
        branch = branch or self.get_current_branch()

        if self.is_branch_pushed(branch):
            return True

        self.console.print(f"[yellow]Branch '{branch}' not pushed to remote[/yellow]")
        return self.push_branch(set_upstream=True)

    def get_branch_status(self, base_branch: str) -> dict[str, Any]:
        """Get comprehensive branch status.

        Args:
            base_branch: Base branch to compare against

        Returns:
            Dict with branch status information
        """
        current = self.get_current_branch()
        ahead = self.get_commits_ahead(base_branch)
        behind = self.get_commits_behind(base_branch)
        pushed = self.is_branch_pushed(current)

        return {
            "current_branch": current,
            "base_branch": base_branch,
            "commits_ahead": ahead,
            "commits_behind": behind,
            "is_pushed": pushed,
            "up_to_date": behind == 0,
            "has_changes": ahead > 0,
        }

    def display_branch_status(self, base_branch: str) -> None:
        """Display branch status to user.

        Args:
            base_branch: Base branch to compare against
        """
        status = self.get_branch_status(base_branch)

        self.console.print("\n[bold]Branch Status[/bold]")
        self.console.print(f"  Current: {status['current_branch']}")
        self.console.print(f"  Base: {status['base_branch']}")
        self.console.print(f"  Ahead: {status['commits_ahead']} commit(s)")
        self.console.print(f"  Behind: {status['commits_behind']} commit(s)")
        self.console.print(f"  Pushed: {'Yes' if status['is_pushed'] else 'No'}")

        if status["commits_behind"] > 0:
            self.console.print(
                f"\n[yellow]Branch is {status['commits_behind']} commit(s) behind {base_branch}[/yellow]"
            )
            self.console.print("Consider syncing before creating/merging PR")
