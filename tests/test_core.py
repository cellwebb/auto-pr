"""Test module for auto_pr.core functionality."""

from unittest.mock import patch

from auto_pr.prompt import build_prompt


def test_build_prompt():
    """Test build_prompt function produces expected output format."""
    status = "On branch main"
    diff = "diff --git a/file.py b/file.py\n+New line"
    hint = "Test hint"

    with patch("auto_pr.preprocess.count_tokens", return_value=42):
        system_prompt, user_prompt = build_prompt(status, diff, hint=hint)

    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)
    assert len(system_prompt) > 0
    assert len(user_prompt) > 0

    assert status in user_prompt
    assert diff in user_prompt
    assert hint in user_prompt

    # Verify system prompt contains role definition
    assert "<role>" in system_prompt or "role" in system_prompt.lower()


def test_build_prompt_without_hint():
    """Test build_prompt works without hint."""
    status = "On branch main"
    diff = "diff --git a/file.py b/file.py\n+New line"

    with patch("auto_pr.preprocess.count_tokens", return_value=42):
        system_prompt, user_prompt = build_prompt(status, diff)

    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)
    assert status in user_prompt
    assert diff in user_prompt
