"""Platform provider registry and detection."""

import logging
import os
import subprocess
from collections.abc import Callable

from auto_pr.platforms.base import BasePlatformProvider
from auto_pr.platforms.errors import PlatformNotFoundError

logger = logging.getLogger(__name__)

PLATFORM_REGISTRY: dict[str, type[BasePlatformProvider]] = {}


def register_platform(name: str) -> Callable[[type[BasePlatformProvider]], type[BasePlatformProvider]]:
    """Decorator to register a platform provider.

    Args:
        name: Platform name (e.g., 'github', 'gitlab')

    Returns:
        Decorator function
    """

    def decorator(cls: type[BasePlatformProvider]) -> type[BasePlatformProvider]:
        PLATFORM_REGISTRY[name] = cls
        return cls

    return decorator


def detect_platform() -> str | None:
    """Detect the Git platform from the repository remote.

    Returns:
        Platform name ('github', 'gitlab', etc.) or None if not detected
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip().lower()

        if "github.com" in remote_url or "github:" in remote_url:
            return "github"
        elif "gitlab.com" in remote_url or "gitlab:" in remote_url:
            return "gitlab"
        elif "bitbucket.org" in remote_url or "bitbucket:" in remote_url:
            return "bitbucket"
        elif "dev.azure.com" in remote_url or "visualstudio.com" in remote_url:
            return "azure"

    except subprocess.CalledProcessError:
        logger.debug("Failed to get git remote URL")
    except FileNotFoundError:
        logger.debug("Git not found")

    return None


def _check_cli_available(command: str) -> bool:
    """Check if a CLI tool is available."""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _check_token_available(env_vars: list[str]) -> bool:
    """Check if any of the token environment variables are set."""
    return any(os.getenv(var) for var in env_vars)


def get_platform_provider(platform: str | None = None) -> BasePlatformProvider:
    """Get a platform provider instance.

    Args:
        platform: Platform name. If None, auto-detect from git remote.

    Returns:
        Platform provider instance

    Raises:
        PlatformNotFoundError: If platform is not available
    """
    if platform is None:
        platform = detect_platform()

    if platform is None:
        raise PlatformNotFoundError("unknown")

    if platform not in PLATFORM_REGISTRY:
        available = ", ".join(PLATFORM_REGISTRY.keys()) if PLATFORM_REGISTRY else "none"
        raise PlatformNotFoundError(f"{platform} (available: {available})")

    provider_class = PLATFORM_REGISTRY[platform]
    provider = provider_class()

    if not provider.is_available():
        raise PlatformNotFoundError(platform)

    return provider


def get_available_platforms() -> list[str]:
    """Get list of available platform providers.

    Returns:
        List of platform names that are available
    """
    available = []
    for name, provider_class in PLATFORM_REGISTRY.items():
        try:
            provider = provider_class()
            if provider.is_available():
                available.append(name)
        except Exception:
            pass
    return available
