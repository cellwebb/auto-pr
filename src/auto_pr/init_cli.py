"""CLI for initializing auto-pr configuration interactively."""

from pathlib import Path
from typing import cast

import click
import questionary
from dotenv import dotenv_values

from auto_pr.language_cli import configure_language_init_workflow
from auto_pr.model_cli import _configure_model

AUTO_PR_ENV_PATH = Path.home() / ".auto-pr.env"


def _prompt_required_text(prompt: str) -> str | None:
    """Prompt until a non-empty string is provided or the user cancels."""
    while True:
        response = questionary.text(prompt).ask()
        if response is None:
            return None
        value = response.strip()
        if value:
            return cast(str, value)
        click.echo("A value is required. Please try again.")


def _load_existing_env() -> dict[str, str]:
    """Ensure the env file exists and return its current values."""
    existing_env: dict[str, str] = {}
    if AUTO_PR_ENV_PATH.exists():
        click.echo(f"$HOME/.auto-pr.env already exists at {AUTO_PR_ENV_PATH}. Values will be updated.")
        existing_env = {k: v for k, v in dotenv_values(str(AUTO_PR_ENV_PATH)).items() if v is not None}
    else:
        AUTO_PR_ENV_PATH.touch()
        click.echo(f"Created $HOME/.auto-pr.env at {AUTO_PR_ENV_PATH}.")
    return existing_env


def _configure_language(existing_env: dict[str, str]) -> None:
    """Run the language configuration flow using consolidated logic."""
    click.echo("\n")

    # Use the consolidated language configuration from language_cli
    success = configure_language_init_workflow(AUTO_PR_ENV_PATH)

    if not success:
        click.echo("Language configuration cancelled or failed.")
    else:
        click.echo("Language configuration completed.")


@click.command()
def init() -> None:
    """Interactively set up $HOME/.auto-pr.env for auto-pr."""
    click.echo("Welcome to Auto-PR initialization!\n")

    existing_env = _load_existing_env()

    if not _configure_model(existing_env):
        click.echo("Model configuration cancelled. Exiting.")
        return

    _configure_language(existing_env)

    click.echo("\nAuto-PR environment setup complete 🎉")
    click.echo("Configuration saved to:")
    click.echo(f"  {AUTO_PR_ENV_PATH}")
    click.echo("\nYou can now run 'auto-pr' in any Git repository to generate PRs and merge commits.")
    click.echo("Run 'auto-pr --help' to see available options.")
