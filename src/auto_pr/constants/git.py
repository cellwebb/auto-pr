"""Constants for git operations and message generation."""

from enum import Enum


class FileStatus(Enum):
    """File status for Git operations."""

    MODIFIED = "M"
    ADDED = "A"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNTRACKED = "?"


class MessageConstants:
    """Constants for message generation and cleaning (PRs, commits, etc.)."""

    # Conventional commit type prefixes (useful for merge commits)
    CONVENTIONAL_PREFIXES: list[str] = [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "merge",  # For merge commits
    ]

    # XML tags that may leak from prompt templates into AI responses
    XML_TAGS_TO_REMOVE: list[str] = [
        "<git-status>",
        "</git-status>",
        "<git_status>",
        "</git_status>",
        "<git-diff>",
        "</git-diff>",
        "<git_diff>",
        "</git_diff>",
        "<repository_context>",
        "</repository_context>",
        "<instructions>",
        "</instructions>",
        "<format>",
        "</format>",
        "<conventions>",
        "</conventions>",
        "<hint>",
        "</hint>",
        "<language_instructions>",
        "</language_instructions>",
    ]

    # Indicators that mark the start of the actual message in AI responses
    MESSAGE_INDICATORS: list[str] = [
        "# Your message:",
        "Your message:",
        "The message is:",
        "Here's the message:",
        "Message:",
        "Final message:",
        "# Message",
        # Legacy commit indicators
        "# Your commit message:",
        "Your commit message:",
        "The commit message is:",
        "Here's the commit message:",
        "Commit message:",
        "Final commit message:",
        "# Commit Message",
    ]


# Legacy alias for compatibility
CommitMessageConstants = MessageConstants
