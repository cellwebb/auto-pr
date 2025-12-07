"""Workflow context objects to reduce parameter explosion.

These dataclasses bundle related parameters that are passed through
the PR workflow, making function signatures cleaner and more maintainable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import will be updated as we implement PR workflows
    pass


@dataclass(frozen=True)
class PRCreationOptions:
    """Options for PR creation workflow."""

    base_branch: str = "main"
    title_only: bool = False
    draft: bool = False
    interactive: bool = False
    dry_run: bool = False
    show_prompt: bool = False
    language: str | None = None
    model: str | None = None
    quiet: bool = False
    verbose: bool = False
    yes: bool = False
    hint: str = ""


@dataclass(frozen=True)
class PRMergeOptions:
    """Options for PR merge workflow."""

    pr_number: int
    merge_method: str = "merge"
    message_only: bool = False
    show_prompt: bool = False
    language: str | None = None
    model: str | None = None
    quiet: bool = False
    yes: bool = False
    hint: str = ""


@dataclass(frozen=True)
class PRUpdateOptions:
    """Options for PR update workflow."""

    pr_number: int
    show_prompt: bool = False
    language: str | None = None
    model: str | None = None
    quiet: bool = False
    yes: bool = False
    hint: str = ""


# Legacy compatibility - will be removed
@dataclass(frozen=True)
class CLIOptions:
    """Legacy CLI options for compatibility."""

    # Commit-related options (legacy)
    stage_all: bool = False
    group: bool = False
    interactive: bool = False
    model: str | None = None
    hint: str = ""
    one_liner: bool = False
    show_prompt: bool = False
    infer_scope: bool = False
    require_confirmation: bool = True
    push: bool = False
    quiet: bool = False
    dry_run: bool = False
    message_only: bool = False
    verbose: bool = False
    no_verify: bool = False
    skip_secret_scan: bool = False
    language: str | None = None
    hook_timeout: int = 0
