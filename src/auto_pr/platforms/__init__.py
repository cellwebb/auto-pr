"""Platform providers for Git hosting services (GitHub, GitLab, etc.)."""

from auto_pr.platforms.errors import (
    ChecksFailedError,
    MergeConflictError,
    PlatformError,
    PRBlockedError,
    ReviewRequiredError,
)
from auto_pr.platforms.github import GitHubProvider  # noqa: F401 - registers provider
from auto_pr.platforms.models import CheckInfo, PRInfo, ReviewInfo
from auto_pr.platforms.protocol import PlatformProtocol
from auto_pr.platforms.registry import detect_platform, get_platform_provider

__all__ = [
    "CheckInfo",
    "ChecksFailedError",
    "GitHubProvider",
    "MergeConflictError",
    "PlatformError",
    "PlatformProtocol",
    "PRBlockedError",
    "PRInfo",
    "ReviewInfo",
    "ReviewRequiredError",
    "detect_platform",
    "get_platform_provider",
]
