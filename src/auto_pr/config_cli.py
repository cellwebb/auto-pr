"""CLI for managing auto-pr configuration in $HOME/.auto-pr.env."""

import os
from pathlib import Path

import click
from dotenv import load_dotenv, set_key

AUTO_PR_ENV_PATH = Path.home() / ".auto-pr.env"


@click.group()
def config() -> None:
    """Manage auto-pr configuration."""
    pass


@config.command()
def show() -> None:
    """Show all current config values."""
    from dotenv import dotenv_values

    project_env_path = Path(".auto-pr.env")
    user_exists = AUTO_PR_ENV_PATH.exists()
    project_exists = project_env_path.exists()

    if not user_exists and not project_exists:
        click.echo("No $HOME/.auto-pr.env found.")
        click.echo("No project-level .auto-pr.env found.")
        return

    if user_exists:
        click.echo(f"User config ({AUTO_PR_ENV_PATH}):")
        user_config = dotenv_values(str(AUTO_PR_ENV_PATH))
        for key, value in sorted(user_config.items()):
            if value is not None:
                if any(sensitive in key.lower() for sensitive in ["key", "token", "secret"]):
                    display_value = "***hidden***"
                else:
                    display_value = value
                click.echo(f"  {key}={display_value}")
    else:
        click.echo("No $HOME/.auto-pr.env found.")

    if project_exists:
        if user_exists:
            click.echo("")
        click.echo("Project config (./.auto-pr.env):")
        project_config = dotenv_values(str(project_env_path))
        for key, value in sorted(project_config.items()):
            if value is not None:
                if any(sensitive in key.lower() for sensitive in ["key", "token", "secret"]):
                    display_value = "***hidden***"
                else:
                    display_value = value
                click.echo(f"  {key}={display_value}")
        click.echo("")
        click.echo("Note: Project-level .auto-pr.env overrides $HOME/.auto-pr.env values for any duplicated variables.")
    else:
        click.echo("No project-level .auto-pr.env found.")


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a config KEY to VALUE in $HOME/.auto-pr.env."""
    AUTO_PR_ENV_PATH.touch(exist_ok=True)
    set_key(str(AUTO_PR_ENV_PATH), key, value)
    click.echo(f"Set {key} in $HOME/.auto-pr.env")


@config.command()
@click.argument("key")
def get(key: str) -> None:
    """Get a config value by KEY."""
    load_dotenv(AUTO_PR_ENV_PATH, override=True)
    value = os.getenv(key)
    if value is None:
        click.echo(f"{key} not set.")
    else:
        click.echo(value)


@config.command()
@click.argument("key")
def unset(key: str) -> None:
    """Remove a config KEY from $HOME/.auto-pr.env."""
    if not AUTO_PR_ENV_PATH.exists():
        click.echo("No $HOME/.auto-pr.env found.")
        return
    lines = AUTO_PR_ENV_PATH.read_text().splitlines()
    new_lines = [line for line in lines if not line.strip().startswith(f"{key}=")]
    AUTO_PR_ENV_PATH.write_text("\n".join(new_lines) + "\n")
    click.echo(f"Unset {key} in $HOME/.auto-pr.env")
