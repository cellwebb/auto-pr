"""Auto-PR - Generate pull requests and merge commits using AI."""

from auto_pr import init_cli
from auto_pr.__version__ import __version__
from auto_pr.ai import generate_commit_message
from auto_pr.prompt import build_prompt

__all__ = [
    "__version__",
    "build_prompt",
    "generate_commit_message",
    "init_cli",
]
