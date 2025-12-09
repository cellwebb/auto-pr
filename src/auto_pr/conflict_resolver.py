"""Merge conflict detection and resolution handling."""

import logging
from dataclasses import dataclass

import click
from rich.console import Console
from rich.panel import Panel

from auto_pr.errors import GitError
from auto_pr.git import run_git_command
from auto_pr.platforms.protocol import PlatformProtocol

logger = logging.getLogger(__name__)


@dataclass
class ConflictInfo:
    """Information about a merge conflict."""

    file_path: str
    ours_content: str | None = None
    theirs_content: str | None = None
    conflict_markers: int = 0


class ConflictResolver:
    """Handles merge conflict detection and resolution."""

    def __init__(
        self,
        platform: PlatformProtocol | None = None,
        console: Console | None = None,
    ) -> None:
        self.platform = platform
        self.console = console or Console()

    def detect_local_conflicts(self) -> list[str]:
        """Detect merge conflicts in the local working tree.

        Returns:
            List of file paths with conflicts
        """
        try:
            output = run_git_command(["diff", "--name-only", "--diff-filter=U"])
            if not output.strip():
                return []
            return [f.strip() for f in output.strip().split("\n") if f.strip()]
        except GitError:
            return []

    def detect_conflicts_with_base(self, base_branch: str) -> list[str]:
        """Detect potential conflicts by attempting a merge.

        Args:
            base_branch: Base branch to check conflicts against

        Returns:
            List of conflicting file paths
        """
        try:
            run_git_command(["fetch", "origin", base_branch], silent=True)
        except GitError as e:
            logger.warning(f"Failed to fetch {base_branch}: {e}")

        try:
            run_git_command(
                ["merge", "--no-commit", "--no-ff", f"origin/{base_branch}"],
                silent=True,
            )
            run_git_command(["merge", "--abort"], silent=True)
            return []

        except GitError:
            conflicts = self.detect_local_conflicts()
            try:
                run_git_command(["merge", "--abort"], silent=True)
            except GitError:
                pass
            return conflicts

    def get_conflict_details(self, file_path: str) -> ConflictInfo:
        """Get detailed information about a conflict.

        Args:
            file_path: Path to the conflicting file

        Returns:
            ConflictInfo with details
        """
        try:
            with open(file_path) as f:
                content = f.read()
        except OSError:
            return ConflictInfo(file_path=file_path)

        marker_count = content.count("<<<<<<<") + content.count(">>>>>>>")

        return ConflictInfo(
            file_path=file_path,
            conflict_markers=marker_count // 2,
        )

    def display_conflicts(self, conflicts: list[str], base_branch: str) -> None:
        """Display conflict information to the user.

        Args:
            conflicts: List of conflicting file paths
            base_branch: Base branch name
        """
        self.console.print()
        self.console.print("[bold red]Merge conflicts detected![/bold red]")
        self.console.print()
        self.console.print(f"[yellow]Conflicts with {base_branch}:[/yellow]")

        for i, file_path in enumerate(conflicts, 1):
            self.console.print(f"  {i}. {file_path}")

        self.console.print()

    def display_resolution_options(self, base_branch: str) -> None:
        """Display available resolution options.

        Args:
            base_branch: Base branch name
        """
        options = f"""[bold]Resolution options:[/bold]

1. [cyan]Rebase[/cyan] (recommended for linear history):
   git fetch origin {base_branch}
   git rebase origin/{base_branch}

2. [cyan]Merge[/cyan] (preserves branch history):
   git fetch origin {base_branch}
   git merge origin/{base_branch}

3. [cyan]Manual resolution[/cyan]:
   - Edit conflicting files to resolve markers
   - git add <resolved-files>
   - git commit"""

        self.console.print(Panel(options, title="How to Resolve"))

    def attempt_auto_resolution(
        self,
        base_branch: str,
        strategy: str = "rebase",
    ) -> tuple[bool, list[str]]:
        """Attempt automatic conflict resolution.

        Args:
            base_branch: Base branch to sync with
            strategy: Resolution strategy ('rebase' or 'merge')

        Returns:
            Tuple of (success, remaining_conflicts)
        """
        self.console.print(f"\n[cyan]Attempting {strategy} resolution...[/cyan]")

        try:
            run_git_command(["fetch", "origin", base_branch], silent=True)
        except GitError as e:
            self.console.print(f"[red]Failed to fetch: {e}[/red]")
            return False, []

        if strategy == "rebase":
            return self._attempt_rebase(base_branch)
        elif strategy == "merge":
            return self._attempt_merge(base_branch)
        else:
            self.console.print(f"[red]Unknown strategy: {strategy}[/red]")
            return False, []

    def _attempt_rebase(self, base_branch: str) -> tuple[bool, list[str]]:
        """Attempt rebase resolution."""
        try:
            run_git_command(["rebase", f"origin/{base_branch}"])
            self.console.print("[green]Rebase successful![/green]")
            return True, []
        except GitError:
            conflicts = self.detect_local_conflicts()
            if conflicts:
                self.console.print(f"[yellow]Rebase paused with {len(conflicts)} conflict(s)[/yellow]")
                try:
                    run_git_command(["rebase", "--abort"], silent=True)
                except GitError:
                    pass
            return False, conflicts

    def _attempt_merge(self, base_branch: str) -> tuple[bool, list[str]]:
        """Attempt merge resolution."""
        try:
            run_git_command(["merge", f"origin/{base_branch}"])
            self.console.print("[green]Merge successful![/green]")
            return True, []
        except GitError:
            conflicts = self.detect_local_conflicts()
            if conflicts:
                self.console.print(f"[yellow]Merge paused with {len(conflicts)} conflict(s)[/yellow]")
                try:
                    run_git_command(["merge", "--abort"], silent=True)
                except GitError:
                    pass
            return False, conflicts

    def interactive_resolution(
        self,
        conflicts: list[str],
        base_branch: str,
    ) -> bool:
        """Guide user through interactive conflict resolution.

        Args:
            conflicts: List of conflicting files
            base_branch: Base branch name

        Returns:
            True if resolution was successful
        """
        self.display_conflicts(conflicts, base_branch)

        choice = click.prompt(
            "How would you like to resolve?",
            type=click.Choice(["rebase", "merge", "manual", "abort"]),
            default="rebase",
        )

        if choice == "abort":
            self.console.print("[yellow]Resolution aborted[/yellow]")
            return False

        if choice == "manual":
            self.display_resolution_options(base_branch)
            self.console.print("\n[yellow]Please resolve conflicts manually.[/yellow]")
            self.console.print("Run 'auto-pr merge-pr' again when conflicts are resolved.")
            return False

        success, remaining = self.attempt_auto_resolution(base_branch, choice)

        if not success and remaining:
            self.console.print("\n[red]Auto-resolution failed. Manual intervention required.[/red]")
            self.display_resolution_options(base_branch)

            resolve_manually = click.confirm(
                "Would you like to resolve manually now?",
                default=False,
            )

            if resolve_manually:
                return self._guide_manual_resolution(remaining)

        return success

    def _guide_manual_resolution(self, conflicts: list[str]) -> bool:
        """Guide user through manual file-by-file resolution.

        Args:
            conflicts: List of conflicting files

        Returns:
            True if all conflicts resolved
        """
        self.console.print("\n[cyan]Manual conflict resolution[/cyan]")
        self.console.print("For each file, choose how to resolve the conflict.\n")

        for i, file_path in enumerate(conflicts, 1):
            self.console.print(f"\n[bold]File {i}/{len(conflicts)}: {file_path}[/bold]")

            try:
                diff = run_git_command(["diff", file_path])
                if diff:
                    self.console.print(Panel(diff[:2000], title="Conflict diff"))
            except GitError:
                pass

            choice = click.prompt(
                "Resolve using",
                type=click.Choice(["ours", "theirs", "edit", "skip"]),
                default="edit",
            )

            if choice == "ours":
                try:
                    run_git_command(["checkout", "--ours", file_path])
                    run_git_command(["add", file_path])
                    self.console.print(f"[green]Kept our version of {file_path}[/green]")
                except GitError as e:
                    self.console.print(f"[red]Failed: {e}[/red]")
                    return False

            elif choice == "theirs":
                try:
                    run_git_command(["checkout", "--theirs", file_path])
                    run_git_command(["add", file_path])
                    self.console.print(f"[green]Accepted their version of {file_path}[/green]")
                except GitError as e:
                    self.console.print(f"[red]Failed: {e}[/red]")
                    return False

            elif choice == "edit":
                self.console.print(f"[yellow]Please edit {file_path} to resolve conflicts[/yellow]")
                click.prompt("Press Enter when done", default="", show_default=False)
                try:
                    run_git_command(["add", file_path])
                except GitError as e:
                    self.console.print(f"[red]Failed to stage: {e}[/red]")
                    return False

            elif choice == "skip":
                self.console.print(f"[yellow]Skipping {file_path}[/yellow]")
                continue

        remaining = self.detect_local_conflicts()
        if remaining:
            self.console.print(f"\n[red]{len(remaining)} conflict(s) still unresolved[/red]")
            return False

        self.console.print("\n[green]All conflicts resolved![/green]")
        return True

    def push_resolution(self, force: bool = False) -> bool:
        """Push resolved changes.

        Args:
            force: Use force push (for rebase)

        Returns:
            True if push succeeded
        """
        try:
            args = ["push"]
            if force:
                args.append("--force-with-lease")

            run_git_command(args)
            self.console.print("[green]Changes pushed successfully[/green]")
            return True

        except GitError as e:
            self.console.print(f"[red]Push failed: {e}[/red]")
            if "rejected" in str(e).lower() and not force:
                self.console.print("[yellow]Try using force push after rebase[/yellow]")
            return False


def resolve_pr_conflicts(
    platform: PlatformProtocol,
    pr_number: int,
    auto_resolve: bool = False,
    strategy: str = "rebase",
    console: Console | None = None,
) -> bool:
    """Resolve conflicts for a PR.

    Args:
        platform: Platform provider
        pr_number: PR number
        auto_resolve: Attempt automatic resolution
        strategy: Resolution strategy for auto-resolve
        console: Console for output

    Returns:
        True if conflicts were resolved
    """
    console = console or Console()
    resolver = ConflictResolver(platform, console)

    pr_info = platform.get_pr(pr_number)

    if not pr_info.has_conflicts:
        console.print("[green]No conflicts detected[/green]")
        return True

    base_branch = pr_info.base_branch

    conflicts = resolver.detect_conflicts_with_base(base_branch)
    if not conflicts:
        console.print("[yellow]PR shows conflicts but local detection found none[/yellow]")
        console.print("Try fetching latest changes and checking again.")
        return False

    if auto_resolve:
        success, remaining = resolver.attempt_auto_resolution(base_branch, strategy)
        if success:
            if resolver.push_resolution(force=(strategy == "rebase")):
                console.print(f"[green]Conflicts resolved and pushed for PR #{pr_number}[/green]")
                return True
        return False

    return resolver.interactive_resolution(conflicts, base_branch)
