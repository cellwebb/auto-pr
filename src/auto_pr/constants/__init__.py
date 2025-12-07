"""Constants for the Auto-PR project.

This package provides all constants used throughout auto_pr, organized into
logical modules:

- defaults: Environment defaults, provider defaults, logging, and utility constants
- file_patterns: File pattern matching and importance weighting
- languages: Language code mappings for internationalization
- git: Git file status and message generation constants

All constants are re-exported from this package for backward compatibility.
"""

from auto_pr.constants.defaults import EnvDefaults, Logging, ProviderDefaults, Utility
from auto_pr.constants.file_patterns import CodePatternImportance, FilePatterns, FileTypeImportance
from auto_pr.constants.git import CommitMessageConstants, FileStatus, MessageConstants
from auto_pr.constants.languages import Languages

__all__ = [
    # From defaults
    "EnvDefaults",
    "ProviderDefaults",
    "Logging",
    "Utility",
    # From file_patterns
    "FilePatterns",
    "FileTypeImportance",
    "CodePatternImportance",
    # From languages
    "Languages",
    # From git
    "FileStatus",
    "MessageConstants",
    "CommitMessageConstants",
]
