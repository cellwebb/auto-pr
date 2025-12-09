# flake8: noqa: E304

"""CLI entry point for auto-pr.

Defines the Click-based command-line interface and delegates execution to the main workflow.
"""

import logging
import sys

import click
from rich.console import Console

from auto_pr import __version__
from auto_pr.auth_cli import auth as auth_cli
from auto_pr.config import AutoPRConfig, load_config
from auto_pr.config_cli import config as config_cli
from auto_pr.init_cli import init as init_cli
from auto_pr.language_cli import language as language_cli
from auto_pr.main import (
    create_branch_workflow,
    create_pr_workflow,
    merge_pr_workflow,
    update_pr_workflow,
)
from auto_pr.model_cli import model as model_cli
from auto_pr.utils import setup_logging

config: AutoPRConfig = load_config()
logger = logging.getLogger(__name__)
console = Console()


@click.group(invoke_without_command=True, context_settings={"ignore_unknown_options": True})
@click.option("--version", is_flag=True, help="Show the version of Auto-PR tool")
@click.pass_context
def cli(ctx: click.Context, version: bool = False) -> None:
    """Auto-PR - Generate pull requests and merge commits with AI."""
    if ctx.invoked_subcommand is None:
        if version:
            print(f"Auto-PR version: {__version__}")
            sys.exit(0)
        console.print("Use 'auto-pr --help' to see available commands.")
        console.print("Main commands:")
        console.print("  init           - Configure AI provider and settings")
        console.print("  create-branch  - Generate a branch name from changes")
        console.print("  create-pr      - Generate and create a pull request")
        console.print("  merge-pr       - Generate a merge commit for a PR")
        console.print("  update-pr      - Update an existing PR description")


cli.add_command(auth_cli)
cli.add_command(config_cli)
cli.add_command(init_cli)
cli.add_command(language_cli)
cli.add_command(model_cli)


@cli.command()
@click.option("--base", "-b", default=None, help="Base branch to compare against (default: repo default)")
@click.option("--title-only", is_flag=True, help="Generate only PR title, not full description")
@click.option("--draft", is_flag=True, help="Create PR as draft")
@click.option("--interactive", "-i", is_flag=True, help="Ask interactive questions to gather more context")
@click.option("--dry-run", is_flag=True, help="Preview PR content without creating")
@click.option("--show-prompt", is_flag=True, help="Show the prompt sent to the LLM")
@click.option(
    "--language", "-l", help="Override the language for PR description (e.g., 'Spanish', 'es', 'zh-CN', 'ja')"
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--model", "-m", help="Override the default model (format: 'provider:model_name')")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Generate detailed PR description with testing instructions and impact analysis",
)
@click.option("--hint", "-h", default="", help="Additional context to guide the AI")
@click.option("--reviewer", "-r", "reviewers", multiple=True, help="Request reviewers (can be used multiple times)")
@click.option("--label", "labels", multiple=True, help="Add labels (can be used multiple times)")
@click.option("--wait-checks", "-w", is_flag=True, help="Wait for CI checks after creating PR")
@click.option("--sync", is_flag=True, help="Sync branch with base before creating PR")
@click.pass_context
def create_pr(
    ctx: click.Context,
    base: str | None = None,
    title_only: bool = False,
    draft: bool = False,
    interactive: bool = False,
    dry_run: bool = False,
    show_prompt: bool = False,
    language: str | None = None,
    yes: bool = False,
    model: str | None = None,
    quiet: bool = False,
    verbose: bool = False,
    hint: str = "",
    reviewers: tuple[str, ...] = (),
    labels: tuple[str, ...] = (),
    wait_checks: bool = False,
    sync: bool = False,
) -> None:
    """Generate and create a pull request using AI."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting PR creation workflow")

    base_branch = base or config.get("default_base_branch") or "main"

    exit_code = create_pr_workflow(
        base_branch=base_branch,
        title_only=title_only,
        draft=draft,
        interactive=interactive,
        dry_run=dry_run,
        show_prompt=show_prompt,
        language=language,
        model=model,
        quiet=quiet,
        verbose=verbose,
        yes=yes,
        hint=hint,
        reviewers=list(reviewers) if reviewers else None,
        labels=list(labels) if labels else None,
        wait_for_checks=wait_checks,
        sync_branch=sync,
    )
    sys.exit(exit_code)


@cli.command()
@click.option("--pr-number", "-n", required=True, type=int, help="Pull request number to merge")
@click.option(
    "--merge-method",
    type=click.Choice(["merge", "squash", "rebase"]),
    default=None,
    help="Merge strategy to use (default: config or 'merge')",
)
@click.option("--message-only", is_flag=True, help="Generate only merge commit message without merging")
@click.option("--show-prompt", is_flag=True, help="Show the prompt sent to the LLM")
@click.option("--language", "-l", help="Override the language for merge commit message")
@click.option("--model", "-m", help="Override the default model (format: 'provider:model_name')")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--hint", "-h", default="", help="Additional context to guide the AI")
@click.option("--wait-checks/--no-wait-checks", default=True, help="Wait for CI checks before merging")
@click.option("--auto-resolve", is_flag=True, help="Automatically resolve conflicts via rebase")
@click.option("--delete-branch", "-d", is_flag=True, help="Delete the head branch after merging")
@click.option("--check-timeout", default=600, type=int, help="Timeout for waiting on checks (seconds)")
@click.pass_context
def merge_pr(
    ctx: click.Context,
    pr_number: int,
    merge_method: str | None = None,
    message_only: bool = False,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
    hint: str = "",
    wait_checks: bool = True,
    auto_resolve: bool = False,
    delete_branch: bool = False,
    check_timeout: int = 600,
) -> None:
    """Generate a merge commit message using AI and merge the PR."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting PR merge workflow")

    method = merge_method or config.get("default_merge_method") or "merge"
    delete = delete_branch or config.get("delete_branch_after_merge", False)

    exit_code = merge_pr_workflow(
        pr_number=pr_number,
        merge_method=method,
        message_only=message_only,
        show_prompt=show_prompt,
        language=language,
        model=model,
        quiet=quiet,
        yes=yes,
        hint=hint,
        wait_for_checks=wait_checks,
        auto_resolve_conflicts=auto_resolve,
        delete_branch=delete,
        check_timeout=check_timeout,
    )
    sys.exit(exit_code)


@cli.command()
@click.option("--pr-number", "-n", type=int, help="Pull request number to update (auto-detects from current branch)")
@click.option("--show-prompt", is_flag=True, help="Show the prompt sent to the LLM")
@click.option("--language", "-l", help="Override the language for PR description")
@click.option("--model", "-m", help="Override the default model (format: 'provider:model_name')")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--hint", "-h", default="", help="Additional context to guide the AI")
@click.option("--verbose", "-v", is_flag=True, help="Generate detailed PR description")
@click.pass_context
def update_pr(
    ctx: click.Context,
    pr_number: int | None = None,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
    hint: str = "",
    verbose: bool = False,
) -> None:
    """Update an existing pull request description using AI."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting PR update workflow")

    exit_code = update_pr_workflow(
        pr_number=pr_number,
        show_prompt=show_prompt,
        language=language,
        model=model,
        quiet=quiet,
        yes=yes,
        hint=hint,
        verbose=verbose,
    )
    sys.exit(exit_code)


@cli.command()
@click.option("--pr-number", "-n", type=int, help="PR number to check status for")
@click.pass_context
def status(ctx: click.Context, pr_number: int | None = None) -> None:
    """Show PR status and workflow state."""
    setup_logging(config["log_level"])

    from auto_pr.branch_manager import BranchManager
    from auto_pr.check_monitor import CheckMonitor
    from auto_pr.platforms import get_platform_provider
    from auto_pr.platforms.errors import PlatformError
    from auto_pr.pr_state_machine import PRStateMachine
    from auto_pr.review_manager import ReviewManager

    try:
        platform = get_platform_provider()
    except PlatformError as e:
        console.print(f"[red]{e.message}[/red]")
        sys.exit(1)

    branch_manager = BranchManager(console)

    if pr_number:
        try:
            pr_info = platform.get_pr(pr_number)
        except PlatformError as e:
            console.print(f"[red]{e.message}[/red]")
            sys.exit(1)

        console.print(f"\n[bold]PR #{pr_number}: {pr_info.title}[/bold]")
        console.print(f"  URL: {pr_info.url}")
        console.print(f"  Branch: {pr_info.head_branch} → {pr_info.base_branch}")

        state_machine = PRStateMachine.from_pr_info(pr_info)
        console.print(f"  State: {state_machine.get_state_description()}")

        if pr_info.has_conflicts:
            console.print("  [red]Has merge conflicts[/red]")

        check_monitor = CheckMonitor(platform, console)
        checks = check_monitor.get_checks(pr_number)
        if checks:
            summary = check_monitor.summarize_checks(checks)
            console.print(f"  Checks: {summary.passed} passed, {summary.failed} failed, {summary.pending} pending")

        review_manager = ReviewManager(platform, console)
        review_manager.display_review_status(pr_number)

    else:
        current_branch = branch_manager.get_current_branch()
        console.print(f"\n[bold]Current branch: {current_branch}[/bold]")

        default_branch = platform.get_default_branch()
        branch_manager.display_branch_status(default_branch)

        existing_pr = platform.find_pr_for_branch(current_branch)
        if existing_pr:
            console.print(f"\n[cyan]Existing PR: #{existing_pr.number} - {existing_pr.title}[/cyan]")
            console.print(f"  URL: {existing_pr.url}")
        else:
            console.print("\n[yellow]No open PR for this branch[/yellow]")


@cli.command()
@click.option("--hint", "-h", default="", help="Additional context to guide the AI")
@click.option("--model", "-m", help="Override the default model (format: 'provider:model_name')")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--show-prompt", is_flag=True, help="Show the prompt sent to the LLM")
@click.option("--include-unstaged", "-u", is_flag=True, help="Include unstaged changes in analysis")
@click.option("--no-checkout", is_flag=True, help="Create branch without checking it out")
@click.pass_context
def create_branch(
    ctx: click.Context,
    hint: str = "",
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
    show_prompt: bool = False,
    include_unstaged: bool = False,
    no_checkout: bool = False,
) -> None:
    """Generate a branch name from your changes and create the branch."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting branch creation workflow")

    exit_code = create_branch_workflow(
        hint=hint,
        model=model,
        quiet=quiet,
        yes=yes,
        show_prompt=show_prompt,
        include_unstaged=include_unstaged,
        checkout=not no_checkout,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
