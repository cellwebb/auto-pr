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

# from auto_pr.main import main  # Will be updated for PR workflows
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
        console.print("  init         - Configure AI provider and settings")
        console.print("  create-pr    - Generate and create a pull request")
        console.print("  merge-pr     - Generate a merge commit for a PR")
        console.print("  update-pr    - Update an existing PR description")


# Add subcommands
cli.add_command(auth_cli)
cli.add_command(config_cli)
cli.add_command(init_cli)
cli.add_command(language_cli)
cli.add_command(model_cli)


@cli.command()
@click.option("--base", "-b", default="main", help="Base branch to compare against (default: main)")
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
@click.pass_context
def create_pr(
    ctx: click.Context,
    base: str = "main",
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
) -> None:
    """Generate and create a pull request using AI."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting PR creation workflow")

    # Will be implemented by updating main.py
    console.print("[yellow]PR creation workflow not yet implemented. This is a work in progress.[/yellow]")


@cli.command()
@click.option("--pr-number", "-n", required=True, help="Pull request number to merge")
@click.option(
    "--merge-method",
    type=click.Choice(["merge", "squash", "rebase"]),
    default="merge",
    help="Merge strategy to use (default: merge)",
)
@click.option("--message-only", is_flag=True, help="Generate only merge commit message without merging")
@click.option("--show-prompt", is_flag=True, help="Show the prompt sent to the LLM")
@click.option("--language", "-l", help="Override the language for merge commit message")
@click.option("--model", "-m", help="Override the default model (format: 'provider:model_name')")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def merge_pr(
    ctx: click.Context,
    pr_number: int,
    merge_method: str = "merge",
    message_only: bool = False,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
) -> None:
    """Generate a merge commit message using AI and merge the PR."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting PR merge workflow")

    # Will be implemented by updating main.py
    console.print("[yellow]PR merge workflow not yet implemented. This is a work in progress.[/yellow]")


@cli.command()
@click.option("--pr-number", "-n", required=True, help="Pull request number to update")
@click.option("--show-prompt", is_flag=True, help="Show the prompt sent to the LLM")
@click.option("--language", "-l", help="Override the language for PR description")
@click.option("--model", "-m", help="Override the default model (format: 'provider:model_name')")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def update_pr(
    ctx: click.Context,
    pr_number: int,
    show_prompt: bool = False,
    language: str | None = None,
    model: str | None = None,
    quiet: bool = False,
    yes: bool = False,
) -> None:
    """Update an existing pull request description using AI."""
    setup_logging("ERROR" if quiet else config["log_level"])
    logger.info("Starting PR update workflow")

    # Will be implemented by updating main.py
    console.print("[yellow]PR update workflow not yet implemented. This is a work in progress.[/yellow]")


if __name__ == "__main__":
    cli()
