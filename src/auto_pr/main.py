#!/usr/bin/env python3
"""Business logic for auto-pr: orchestrates PR and merge commit workflows."""

import logging
import re
from functools import lru_cache
from importlib.resources import files

import click
from rich.console import Console
from rich.panel import Panel

from auto_pr.ai import generate_commit_message
from auto_pr.branch_manager import BranchManager
from auto_pr.check_monitor import wait_for_pr_checks
from auto_pr.config import AutoPRConfig, load_config
from auto_pr.conflict_resolver import ConflictResolver, resolve_pr_conflicts
from auto_pr.constants import EnvDefaults
from auto_pr.errors import GitError
from auto_pr.git import run_git_command
from auto_pr.platforms import get_platform_provider
from auto_pr.platforms.errors import (
    ChecksFailedError,
    ChecksPendingError,
    MergeConflictError,
    PlatformError,
    PRBlockedError,
)
from auto_pr.postprocess import clean_commit_message
from auto_pr.pr_state_machine import PRLifecycleState, PRStateMachine
from auto_pr.review_manager import ReviewManager

logger = logging.getLogger(__name__)

config: AutoPRConfig = load_config()
console = Console()


@lru_cache(maxsize=1)
def _load_pr_system_template() -> str:
    return files("auto_pr.templates").joinpath("pr_system_prompt.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_pr_user_template() -> str:
    return files("auto_pr.templates").joinpath("pr_user_prompt.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_merge_system_template() -> str:
    return files("auto_pr.templates").joinpath("merge_system_prompt.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_merge_user_template() -> str:
    return files("auto_pr.templates").joinpath("merge_user_prompt.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_branch_name_template() -> str:
    return files("auto_pr.templates").joinpath("branch_name_prompt.txt").read_text(encoding="utf-8")


def _remove_template_section(template: str, section_name: str) -> str:
    pattern = f"<{section_name}>.*?</{section_name}>\\n?"
    return re.sub(pattern, "", template, flags=re.DOTALL)


def build_pr_prompt(
    diff: str,
    diff_stat: str,
    status: str,
    base_branch: str,
    hint: str = "",
    verbose: bool = False,
    language: str | None = None,
) -> tuple[str, str]:
    """Build PR description prompt."""
    system_template = _load_pr_system_template()
    user_template = _load_pr_user_template()

    if not verbose:
        system_template = _remove_template_section(system_template, "verbose")

    user_template = user_template.replace("<diff></diff>", diff)
    user_template = user_template.replace("<diff_stat></diff_stat>", diff_stat)
    user_template = user_template.replace("<status></status>", status)
    user_template = user_template.replace("<base_branch></base_branch>", base_branch)

    if hint:
        user_template = user_template.replace("<hint_text></hint_text>", hint)
    else:
        user_template = _remove_template_section(user_template, "hint")

    if language:
        user_template = user_template.replace("<language_name></language_name>", language)
    else:
        user_template = _remove_template_section(user_template, "language_instructions")

    return system_template.strip(), user_template.strip()


def build_merge_prompt(
    pr_number: int,
    pr_title: str,
    pr_body: str,
    base_branch: str,
    head_branch: str,
    merge_method: str,
    diff: str = "",
    diff_stat: str = "",
    hint: str = "",
    language: str | None = None,
) -> tuple[str, str]:
    """Build merge commit message prompt."""
    system_template = _load_merge_system_template()
    user_template = _load_merge_user_template()

    user_template = user_template.replace("<pr_number>", str(pr_number))
    user_template = user_template.replace("<pr_title>", pr_title)
    user_template = user_template.replace("<base_branch>", base_branch)
    user_template = user_template.replace("<target_branch>", head_branch)
    user_template = user_template.replace("<merge_method>", merge_method)
    user_template = user_template.replace("<existing_description></existing_description>", pr_body or "")
    user_template = user_template.replace("<diff></diff>", diff)
    user_template = user_template.replace("<diff_stat></diff_stat>", diff_stat)

    if hint:
        user_template = user_template.replace("<hint_text></hint_text>", hint)
    else:
        user_template = _remove_template_section(user_template, "hint")

    if language:
        user_template = user_template.replace("<language_name></language_name>", language)
    else:
        user_template = _remove_template_section(user_template, "language_instructions")

    return system_template.strip(), user_template.strip()


def build_branch_name_prompt(
    diff: str,
    diff_stat: str,
    hint: str = "",
) -> tuple[str, str]:
    """Build branch name generation prompt."""
    system_template = _load_branch_name_template()

    user_prompt = f"""Analyze these changes and generate a descriptive branch name:

<diff_stat>
{diff_stat}
</diff_stat>

<diff>
{diff}
</diff>
"""

    if hint:
        user_prompt += f"""
<context>
Additional context: {hint}
</context>
"""

    user_prompt += "\nGenerate ONLY the branch name, nothing else."

    return system_template.strip(), user_prompt.strip()


def extract_pr_title_body(pr_description: str) -> tuple[str, str]:
    """Extract title from PR description."""
    lines = pr_description.strip().split("\n")

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("## Summary"):
            if i + 1 < len(lines):
                summary_start = i + 1
                summary_lines = []
                for j in range(summary_start, len(lines)):
                    if lines[j].strip().startswith("##"):
                        break
                    if lines[j].strip():
                        summary_lines.append(lines[j].strip())
                if summary_lines:
                    title = summary_lines[0][:72]
                    if len(summary_lines[0]) > 72:
                        title = title.rsplit(" ", 1)[0] + "..."
                    return title, pr_description

    first_line = lines[0].strip() if lines else "Update"
    title = first_line[:72]
    if first_line.startswith("## "):
        title = first_line[3:][:72]
    if len(first_line) > 72:
        title = title.rsplit(" ", 1)[0] + "..."

    return title, pr_description


def create_pr_workflow(
    base_branch: str = "main",
    title_only: bool = False,
    draft: bool = False,
    interactive: bool = False,
    dry_run: bool = False,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    verbose: bool = False,
    yes: bool = False,
    hint: str = "",
    reviewers: list[str] | None = None,
    labels: list[str] | None = None,
    wait_for_checks: bool = False,
    sync_branch: bool = False,
) -> int:
    """Execute PR creation workflow."""
    try:
        platform = get_platform_provider()
    except PlatformError as e:
        console.print(f"[red]{e.message}[/red]")
        if e.suggestion:
            console.print(f"[yellow]{e.suggestion}[/yellow]")
        return 1

    branch_manager = BranchManager(console)
    current_branch = branch_manager.get_current_branch()

    if current_branch == base_branch:
        console.print(f"[red]Cannot create PR from '{base_branch}' to itself[/red]")
        console.print("[yellow]Create a feature branch first: git checkout -b my-feature[/yellow]")
        return 1

    if sync_branch:
        behind = branch_manager.get_commits_behind(base_branch)
        if behind > 0:
            console.print(f"[yellow]Branch is {behind} commit(s) behind {base_branch}[/yellow]")
            if not branch_manager.sync_with_base(base_branch, strategy="rebase"):
                console.print("[red]Failed to sync branch. Resolve conflicts and try again.[/red]")
                return 1

    if not branch_manager.is_branch_pushed(current_branch):
        if not quiet:
            console.print(f"[cyan]Pushing branch '{current_branch}' to remote...[/cyan]")
        if not branch_manager.push_branch(set_upstream=True):
            return 1

    try:
        diff = run_git_command(["diff", f"origin/{base_branch}...{current_branch}"])
        if not diff.strip():
            console.print(f"[yellow]No changes between {base_branch} and {current_branch}[/yellow]")
            return 1

        diff_stat = run_git_command(["diff", "--stat", f"origin/{base_branch}...{current_branch}"])
        status = run_git_command(["diff", "--name-status", f"origin/{base_branch}...{current_branch}"])
    except GitError as e:
        console.print(f"[red]Git error: {e}[/red]")
        return 1

    model = model or config.get("model")
    if not model:
        console.print("[red]No model configured. Run 'auto-pr init' or set AUTO_PR_MODEL[/red]")
        return 2

    language = language or config.get("language")

    if len(diff) > 100000:
        diff = diff[:100000] + "\n... (diff truncated for size)"

    system_prompt, user_prompt = build_pr_prompt(
        diff=diff,
        diff_stat=diff_stat,
        status=status,
        base_branch=base_branch,
        hint=hint,
        verbose=verbose,
        language=language,
    )

    if show_prompt:
        console.print(Panel(user_prompt[:5000], title="PR Prompt (truncated)"))

    if not quiet:
        console.print("[cyan]Generating PR description...[/cyan]")

    try:
        pr_description = generate_commit_message(
            model=model,
            prompt=(system_prompt, user_prompt),
            temperature=config.get("temperature", EnvDefaults.TEMPERATURE),
            max_tokens=config.get("max_output_tokens", EnvDefaults.MAX_OUTPUT_TOKENS),
            max_retries=config.get("max_retries", EnvDefaults.MAX_RETRIES),
            quiet=quiet,
            task_description="PR description",
        )
        pr_description = clean_commit_message(pr_description)
    except Exception as e:
        console.print(f"[red]Failed to generate PR description: {e}[/red]")
        return 4

    title, body = extract_pr_title_body(pr_description)

    if title_only:
        console.print(title)
        return 0

    if not quiet:
        console.print()
        console.print(Panel(f"[bold]{title}[/bold]\n\n{body[:2000]}...", title="PR Preview"))

    if dry_run:
        console.print("\n[yellow]Dry run - PR not created[/yellow]")
        return 0

    if not yes:
        if not click.confirm("\nCreate this PR?", default=True):
            console.print("[yellow]PR creation cancelled[/yellow]")
            return 0

    try:
        pr_info = platform.create_pr(
            title=title,
            body=body,
            head=current_branch,
            base=base_branch,
            draft=draft,
            reviewers=reviewers,
            labels=labels,
        )
        console.print(f"\n[green]PR created: {pr_info.url}[/green]")

        if reviewers:
            console.print(f"[green]Reviewers requested: {', '.join(reviewers)}[/green]")

        if wait_for_checks and not draft:
            console.print("\n[cyan]Waiting for CI checks...[/cyan]")
            try:
                wait_for_pr_checks(platform, pr_info.number, interactive=True, console=console)
            except (ChecksFailedError, ChecksPendingError) as e:
                console.print(f"[yellow]{e.message}[/yellow]")

        return 0

    except PlatformError as e:
        console.print(f"[red]Failed to create PR: {e.message}[/red]")
        return 1


def merge_pr_workflow(
    pr_number: int,
    merge_method: str = "merge",
    message_only: bool = False,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
    hint: str = "",
    wait_for_checks: bool = True,
    auto_resolve_conflicts: bool = False,
    delete_branch: bool = False,
    check_timeout: int = 600,
) -> int:
    """Execute PR merge workflow."""
    try:
        platform = get_platform_provider()
    except PlatformError as e:
        console.print(f"[red]{e.message}[/red]")
        if e.suggestion:
            console.print(f"[yellow]{e.suggestion}[/yellow]")
        return 1

    try:
        pr_info = platform.get_pr(pr_number)
    except PlatformError as e:
        console.print(f"[red]{e.message}[/red]")
        return 1

    if not quiet:
        console.print(f"\n[bold]PR #{pr_number}: {pr_info.title}[/bold]")
        console.print(f"  Branch: {pr_info.head_branch} → {pr_info.base_branch}")

    state_machine = PRStateMachine.from_pr_info(pr_info)
    current_state = state_machine.current_state

    if not quiet:
        console.print(f"  Status: {state_machine.get_state_description()}")

    if current_state == PRLifecycleState.MERGED:
        console.print("[yellow]PR is already merged[/yellow]")
        return 0

    if current_state == PRLifecycleState.CLOSED:
        console.print("[red]PR is closed. Cannot merge.[/red]")
        return 1

    if current_state == PRLifecycleState.DRAFT:
        console.print("[red]PR is a draft. Mark as ready for review first.[/red]")
        return 1

    if current_state == PRLifecycleState.CONFLICT:
        console.print("\n[red]PR has merge conflicts[/red]")

        if auto_resolve_conflicts:
            if resolve_pr_conflicts(platform, pr_number, auto_resolve=True, console=console):
                pr_info = platform.get_pr(pr_number)
                state_machine = PRStateMachine.from_pr_info(pr_info)
                current_state = state_machine.current_state
            else:
                return 1
        else:
            resolver = ConflictResolver(platform, console)
            resolver.display_resolution_options(pr_info.base_branch)
            return 1

    if current_state in (PRLifecycleState.CHECKS_RUNNING, PRLifecycleState.CHECKS_FAILED):
        if wait_for_checks:
            console.print("\n[cyan]Waiting for CI checks...[/cyan]")
            try:
                wait_for_pr_checks(
                    platform,
                    pr_number,
                    timeout=check_timeout,
                    interactive=not yes,
                    console=console,
                )
                pr_info = platform.get_pr(pr_number)
            except ChecksFailedError as e:
                console.print(f"[red]{e.message}[/red]")
                if e.details:
                    console.print(e.details)
                return 1
        elif current_state == PRLifecycleState.CHECKS_FAILED:
            console.print("[red]CI checks failed. Fix before merging or use --ignore-checks[/red]")
            return 1

    if current_state == PRLifecycleState.CHANGES_REQUESTED:
        review_manager = ReviewManager(platform, console)
        requesters = review_manager.get_reviewers_with_changes_requested(pr_number)
        console.print(f"\n[red]Changes requested by: {', '.join(requesters)}[/red]")
        if not yes:
            if not click.confirm("Merge anyway?", default=False):
                return 1

    model = model or config.get("model")
    if not model:
        console.print("[red]No model configured. Run 'auto-pr init' or set AUTO_PR_MODEL[/red]")
        return 2

    language = language or config.get("language")

    try:
        diff = run_git_command(["diff", f"origin/{pr_info.base_branch}...origin/{pr_info.head_branch}"])
        diff_stat = run_git_command(["diff", "--stat", f"origin/{pr_info.base_branch}...origin/{pr_info.head_branch}"])
    except GitError:
        diff = ""
        diff_stat = ""

    if len(diff) > 50000:
        diff = diff[:50000] + "\n... (diff truncated)"

    system_prompt, user_prompt = build_merge_prompt(
        pr_number=pr_number,
        pr_title=pr_info.title,
        pr_body=pr_info.body,
        base_branch=pr_info.base_branch,
        head_branch=pr_info.head_branch,
        merge_method=merge_method,
        diff=diff,
        diff_stat=diff_stat,
        hint=hint,
        language=language,
    )

    if show_prompt:
        console.print(Panel(user_prompt[:3000], title="Merge Prompt (truncated)"))

    if not quiet:
        console.print("\n[cyan]Generating merge commit message...[/cyan]")

    try:
        merge_message = generate_commit_message(
            model=model,
            prompt=(system_prompt, user_prompt),
            temperature=config.get("temperature", EnvDefaults.TEMPERATURE),
            max_tokens=1024,
            max_retries=config.get("max_retries", EnvDefaults.MAX_RETRIES),
            quiet=quiet,
            task_description="merge commit message",
        )
        merge_message = clean_commit_message(merge_message)
    except Exception as e:
        console.print(f"[red]Failed to generate merge message: {e}[/red]")
        return 4

    lines = merge_message.strip().split("\n", 1)
    commit_title = lines[0]
    commit_body = lines[1].strip() if len(lines) > 1 else ""

    if message_only:
        console.print(merge_message)
        return 0

    if not quiet:
        console.print()
        console.print(Panel(merge_message, title="Merge Commit Message"))

    if not yes:
        if not click.confirm(f"\nMerge PR #{pr_number} using {merge_method}?", default=True):
            console.print("[yellow]Merge cancelled[/yellow]")
            return 0

    try:
        success = platform.merge_pr(
            pr_number=pr_number,
            method=merge_method,
            commit_title=commit_title,
            commit_message=commit_body,
            delete_branch=delete_branch,
        )

        if success:
            console.print(f"\n[green]PR #{pr_number} merged successfully![/green]")
            if delete_branch:
                console.print(f"[green]Branch '{pr_info.head_branch}' deleted[/green]")
            return 0
        else:
            console.print("[red]Merge failed[/red]")
            return 1

    except MergeConflictError as e:
        console.print(f"\n[red]Merge conflict: {e.message}[/red]")
        return 1
    except PRBlockedError as e:
        console.print(f"\n[red]PR blocked: {e.message}[/red]")
        if e.details:
            console.print(e.details)
        return 1
    except PlatformError as e:
        console.print(f"[red]Merge failed: {e.message}[/red]")
        return 1


def update_pr_workflow(
    pr_number: int,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
    hint: str = "",
    verbose: bool = False,
) -> int:
    """Execute PR update workflow."""
    try:
        platform = get_platform_provider()
    except PlatformError as e:
        console.print(f"[red]{e.message}[/red]")
        if e.suggestion:
            console.print(f"[yellow]{e.suggestion}[/yellow]")
        return 1

    try:
        pr_info = platform.get_pr(pr_number)
    except PlatformError as e:
        console.print(f"[red]{e.message}[/red]")
        return 1

    if not quiet:
        console.print(f"\n[bold]Updating PR #{pr_number}: {pr_info.title}[/bold]")

    if pr_info.is_merged:
        console.print("[yellow]PR is already merged. Cannot update.[/yellow]")
        return 1

    if not pr_info.is_open:
        console.print("[yellow]PR is closed. Cannot update.[/yellow]")
        return 1

    try:
        run_git_command(["fetch", "origin", pr_info.base_branch, pr_info.head_branch], silent=True)
        diff = run_git_command(["diff", f"origin/{pr_info.base_branch}...origin/{pr_info.head_branch}"])
        diff_stat = run_git_command(["diff", "--stat", f"origin/{pr_info.base_branch}...origin/{pr_info.head_branch}"])
        status = run_git_command(
            ["diff", "--name-status", f"origin/{pr_info.base_branch}...origin/{pr_info.head_branch}"]
        )
    except GitError as e:
        console.print(f"[red]Git error: {e}[/red]")
        return 1

    model = model or config.get("model")
    if not model:
        console.print("[red]No model configured[/red]")
        return 2

    language = language or config.get("language")

    if len(diff) > 100000:
        diff = diff[:100000] + "\n... (diff truncated)"

    system_prompt, user_prompt = build_pr_prompt(
        diff=diff,
        diff_stat=diff_stat,
        status=status,
        base_branch=pr_info.base_branch,
        hint=hint,
        verbose=verbose,
        language=language,
    )

    if show_prompt:
        console.print(Panel(user_prompt[:5000], title="PR Prompt (truncated)"))

    if not quiet:
        console.print("[cyan]Generating updated PR description...[/cyan]")

    try:
        pr_description = generate_commit_message(
            model=model,
            prompt=(system_prompt, user_prompt),
            temperature=config.get("temperature", EnvDefaults.TEMPERATURE),
            max_tokens=config.get("max_output_tokens", EnvDefaults.MAX_OUTPUT_TOKENS),
            max_retries=config.get("max_retries", EnvDefaults.MAX_RETRIES),
            quiet=quiet,
            task_description="PR description",
        )
        pr_description = clean_commit_message(pr_description)
    except Exception as e:
        console.print(f"[red]Failed to generate PR description: {e}[/red]")
        return 4

    title, body = extract_pr_title_body(pr_description)

    if not quiet:
        console.print()
        console.print(Panel(f"[bold]{title}[/bold]\n\n{body[:2000]}...", title="Updated PR"))

    if not yes:
        if not click.confirm("\nUpdate PR with this description?", default=True):
            console.print("[yellow]Update cancelled[/yellow]")
            return 0

    try:
        platform.update_pr(
            pr_number=pr_number,
            title=title,
            body=body,
        )
        console.print(f"\n[green]PR #{pr_number} updated successfully![/green]")
        return 0

    except PlatformError as e:
        console.print(f"[red]Failed to update PR: {e.message}[/red]")
        return 1


def create_branch_workflow(
    hint: str = "",
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
    show_prompt: bool = False,
    include_unstaged: bool = False,
    checkout: bool = True,
) -> int:
    """Generate a branch name from changes and create the branch.

    Args:
        hint: Additional context for branch name generation
        model: Override default AI model
        quiet: Suppress non-error output
        yes: Skip confirmation prompt
        show_prompt: Show the prompt sent to the LLM
        include_unstaged: Include unstaged changes in analysis
        checkout: Checkout the new branch after creation

    Returns:
        Exit code (0 for success)
    """
    from auto_pr.git import get_diff

    model = model or config.get("model")
    if not model:
        console.print("[red]No model configured. Run 'auto-pr init' first.[/red]")
        return 1

    def _get_diff_stat(staged: bool) -> str:
        args = ["diff", "--stat"]
        if staged:
            args.append("--staged")
        try:
            return run_git_command(args)
        except GitError:
            return ""

    if include_unstaged:
        diff = get_diff(staged=False, color=False)
        diff_stat = _get_diff_stat(staged=False)
        if not diff.strip():
            diff = get_diff(staged=True, color=False)
            diff_stat = _get_diff_stat(staged=True)
    else:
        diff = get_diff(staged=True, color=False)
        diff_stat = _get_diff_stat(staged=True)

    if not diff.strip():
        console.print("[yellow]No changes detected. Stage some changes first.[/yellow]")
        console.print("  git add <files>")
        console.print("Or use --include-unstaged to analyze unstaged changes.")
        return 1

    if len(diff) > 50000:
        diff = diff[:50000] + "\n... (diff truncated)"

    system_prompt, user_prompt = build_branch_name_prompt(
        diff=diff,
        diff_stat=diff_stat,
        hint=hint,
    )

    if show_prompt:
        console.print(Panel(user_prompt[:3000], title="Branch Name Prompt"))

    if not quiet:
        console.print("[cyan]Generating branch name...[/cyan]")

    try:
        branch_name = generate_commit_message(
            model=model,
            prompt=(system_prompt, user_prompt),
            temperature=0.3,
            max_tokens=100,
            max_retries=config.get("max_retries", EnvDefaults.MAX_RETRIES),
            quiet=quiet,
            task_description="branch name",
        )
        branch_name = branch_name.strip().strip("`").strip('"').strip("'")
        branch_name = re.sub(r"[^a-z0-9/_-]", "-", branch_name.lower())
        branch_name = re.sub(r"-+", "-", branch_name).strip("-")

        if len(branch_name) > 50:
            branch_name = branch_name[:50].rstrip("-")

    except Exception as e:
        console.print(f"[red]Failed to generate branch name: {e}[/red]")
        return 4

    if not quiet:
        console.print(f"\n[bold green]Generated branch name:[/bold green] {branch_name}")

    if not yes:
        if not click.confirm("\nCreate this branch?", default=True):
            console.print("[yellow]Branch creation cancelled[/yellow]")
            return 0

    try:
        if checkout:
            run_git_command(["checkout", "-b", branch_name])
            console.print(f"\n[green]Created and checked out branch: {branch_name}[/green]")
        else:
            run_git_command(["branch", branch_name])
            console.print(f"\n[green]Created branch: {branch_name}[/green]")
            console.print(f"Run 'git checkout {branch_name}' to switch to it.")

        return 0

    except GitError as e:
        console.print(f"[red]Failed to create branch: {e}[/red]")
        return 1


def main(opts: object) -> int:
    """Legacy main function for compatibility."""
    console.print("[yellow]Auto-PR is being refactored for PR/merge workflows.[/yellow]")
    console.print("Use 'auto-pr create-pr', 'auto-pr merge-pr', or 'auto-pr update-pr'")
    return 0


if __name__ == "__main__":
    pass
