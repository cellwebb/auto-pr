"""OAuth retry handling for expired tokens.

This module provides a unified mechanism for handling OAuth token expiration
across different providers (Claude Code, Qwen, etc.).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from rich.console import Console

from auto_pr.errors import AIError, ConfigError

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class OAuthProviderConfig:
    """Configuration for OAuth retry handling for a specific provider."""

    provider_prefix: str
    display_name: str
    manual_auth_hint: str
    authenticate: Callable[[bool], bool]
    extra_error_check: Callable[[AIError], bool] | None = None


def _create_claude_code_authenticator() -> Callable[[bool], bool]:
    """Create authenticator function for Claude Code."""

    def authenticate(quiet: bool) -> bool:
        from auto_pr.oauth.claude_code import authenticate_and_save

        return authenticate_and_save(quiet=quiet)

    return authenticate


def _create_qwen_authenticator() -> Callable[[bool], bool]:
    """Create authenticator function for Qwen."""

    def authenticate(quiet: bool) -> bool:
        from auto_pr.oauth import QwenOAuthProvider, TokenStore

        try:
            oauth_provider = QwenOAuthProvider(TokenStore())
            oauth_provider.initiate_auth(open_browser=True)
            return True
        except (AIError, ConfigError, OSError):
            return False

    return authenticate


def _claude_code_extra_check(e: AIError) -> bool:
    """Extra check for Claude Code - verify error message contains expired/oauth."""
    error_str = str(e).lower()
    return "expired" in error_str or "oauth" in error_str


OAUTH_PROVIDERS: list[OAuthProviderConfig] = [
    OAuthProviderConfig(
        provider_prefix="claude-code:",
        display_name="Claude Code",
        manual_auth_hint="Run 'auto-pr model' to re-authenticate manually.",
        authenticate=_create_claude_code_authenticator(),
        extra_error_check=_claude_code_extra_check,
    ),
    OAuthProviderConfig(
        provider_prefix="qwen:",
        display_name="Qwen",
        manual_auth_hint="Run 'auto-pr auth qwen login' to re-authenticate manually.",
        authenticate=_create_qwen_authenticator(),
        extra_error_check=None,
    ),
]


def _find_oauth_provider(model: str, error: AIError) -> OAuthProviderConfig | None:
    """Find the OAuth provider config that matches the model and error."""
    if error.error_type != "authentication":
        return None

    for provider in OAUTH_PROVIDERS:
        if not model.startswith(provider.provider_prefix):
            continue
        if provider.extra_error_check and not provider.extra_error_check(error):
            continue
        return provider

    return None


def _attempt_reauth_and_retry(
    provider: OAuthProviderConfig,
    quiet: bool,
    retry_workflow: Callable[[], int],
) -> int:
    """Attempt re-authentication and retry the workflow.

    Args:
        provider: The OAuth provider configuration
        quiet: Whether to suppress output
        retry_workflow: Callable that retries the workflow on success

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    console.print(f"[yellow]⚠ {provider.display_name} OAuth token has expired[/yellow]")
    console.print("[cyan]🔐 Starting automatic re-authentication...[/cyan]")

    try:
        if provider.authenticate(quiet):
            console.print("[green]✓ Re-authentication successful![/green]")
            console.print("[cyan]Retrying operation...[/cyan]\n")
            return retry_workflow()
        else:
            console.print("[red]Re-authentication failed.[/red]")
            console.print(f"[yellow]{provider.manual_auth_hint}[/yellow]")
            return 1
    except (AIError, ConfigError, OSError) as auth_error:
        console.print(f"[red]Re-authentication error: {auth_error}[/red]")
        console.print(f"[yellow]{provider.manual_auth_hint}[/yellow]")
        return 1


def handle_oauth_error(
    e: AIError,
    model: str,
    quiet: bool = False,
    retry_func: Callable[[], int] | None = None,
) -> int:
    """Handle OAuth retry logic for expired tokens.

    Checks if the error is an OAuth-related authentication error for a known
    provider, attempts re-authentication, and retries the workflow on success.

    Args:
        e: The AIError that triggered this handler
        model: The model string (e.g., 'claude-code:claude-3-sonnet')
        quiet: Whether to suppress output
        retry_func: Optional callable to retry the operation after re-auth

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    logger.error(str(e))

    provider = _find_oauth_provider(model, e)

    if provider is None:
        console.print(f"[red]Failed to complete operation: {e!s}[/red]")
        return 1

    if retry_func is not None:
        return _attempt_reauth_and_retry(provider, quiet, retry_func)
    else:
        # Just show the error and hint without retry
        console.print(f"[yellow]⚠ {provider.display_name} OAuth token has expired[/yellow]")
        console.print(f"[yellow]{provider.manual_auth_hint}[/yellow]")
        return 1
