"""Tests for workflow_context.py - 0% coverage, prime target!"""

from dataclasses import fields

import pytest

from auto_pr.workflow_context import (
    CLIOptions,
    PRCreationOptions,
    PRMergeOptions,
    PRUpdateOptions,
)


class TestPRCreationOptions:
    """Test PRCreationOptions dataclass."""

    def test_default_values(self):
        """Test that PRCreationOptions has correct default values."""
        options = PRCreationOptions()

        assert options.base_branch == "main"
        assert options.title_only is False
        assert options.draft is False
        assert options.interactive is False
        assert options.dry_run is False
        assert options.show_prompt is False
        assert options.language is None
        assert options.model is None
        assert options.quiet is False
        assert options.verbose is False
        assert options.yes is False
        assert options.hint == ""

    def test_custom_values(self):
        """Test PRCreationOptions with custom values."""
        options = PRCreationOptions(
            base_branch="develop",
            title_only=True,
            draft=True,
            interactive=True,
            dry_run=True,
            show_prompt=True,
            language="python",
            model="gpt-4",
            quiet=True,
            verbose=True,
            yes=True,
            hint="This is a custom hint",
        )

        assert options.base_branch == "develop"
        assert options.title_only is True
        assert options.draft is True
        assert options.interactive is True
        assert options.dry_run is True
        assert options.show_prompt is True
        assert options.language == "python"
        assert options.model == "gpt-4"
        assert options.quiet is True
        assert options.verbose is True
        assert options.yes is True
        assert options.hint == "This is a custom hint"

    def test_frozen_dataclass(self):
        """Test that PRCreationOptions is frozen and immutable."""
        options = PRCreationOptions()

        with pytest.raises(AttributeError):
            options.base_branch = "develop"

    def test_type_annotations(self):
        """Test that all fields have correct type annotations."""
        # Check that fields exist
        field_names = {f.name for f in fields(PRCreationOptions)}
        expected_fields = {
            "base_branch",
            "title_only",
            "draft",
            "interactive",
            "dry_run",
            "show_prompt",
            "language",
            "model",
            "quiet",
            "verbose",
            "yes",
            "hint",
        }
        assert field_names == expected_fields


class TestPRMergeOptions:
    """Test PRMergeOptions dataclass."""

    def test_required_pr_number(self):
        """Test that PRMergeOptions requires pr_number."""
        # Should work with required pr_number
        options = PRMergeOptions(pr_number=123)
        assert options.pr_number == 123

    def test_default_values(self):
        """Test that PRMergeOptions has correct default values."""
        options = PRMergeOptions(pr_number=123)

        assert options.pr_number == 123
        assert options.merge_method == "merge"
        assert options.message_only is False
        assert options.show_prompt is False
        assert options.language is None
        assert options.model is None
        assert options.quiet is False
        assert options.yes is False
        assert options.hint == ""

    def test_custom_values(self):
        """Test PRMergeOptions with custom values."""
        options = PRMergeOptions(
            pr_number=456,
            merge_method="squash",
            message_only=True,
            show_prompt=True,
            language="javascript",
            model="claude-3",
            quiet=True,
            yes=True,
            hint="Custom merge hint",
        )

        assert options.pr_number == 456
        assert options.merge_method == "squash"
        assert options.message_only is True
        assert options.show_prompt is True
        assert options.language == "javascript"
        assert options.model == "claude-3"
        assert options.quiet is True
        assert options.yes is True
        assert options.hint == "Custom merge hint"

    def test_frozen_dataclass(self):
        """Test that PRMergeOptions is frozen and immutable."""
        options = PRMergeOptions(pr_number=123)

        with pytest.raises(AttributeError):
            options.pr_number = 456


class TestPRUpdateOptions:
    """Test PRUpdateOptions dataclass."""

    def test_required_pr_number(self):
        """Test that PRUpdateOptions requires pr_number."""
        options = PRUpdateOptions(pr_number=789)
        assert options.pr_number == 789

    def test_default_values(self):
        """Test that PRUpdateOptions has correct default values."""
        options = PRUpdateOptions(pr_number=789)

        assert options.pr_number == 789
        assert options.show_prompt is False
        assert options.language is None
        assert options.model is None
        assert options.quiet is False
        assert options.yes is False
        assert options.hint == ""

    def test_custom_values(self):
        """Test PRUpdateOptions with custom values."""
        options = PRUpdateOptions(
            pr_number=999, show_prompt=True, language="go", model="gpt-3.5", quiet=True, yes=True, hint="Update hint"
        )

        assert options.pr_number == 999
        assert options.show_prompt is True
        assert options.language == "go"
        assert options.model == "gpt-3.5"
        assert options.quiet is True
        assert options.yes is True
        assert options.hint == "Update hint"

    def test_frozen_dataclass(self):
        """Test that PRUpdateOptions is frozen and immutable."""
        options = PRUpdateOptions(pr_number=789)

        with pytest.raises(AttributeError):
            options.pr_number = 999


class TestCLIOptions:
    """Test CLIOptions dataclass (legacy compatibility)."""

    def test_default_values(self):
        """Test that CLIOptions has correct default values."""
        options = CLIOptions()

        # Test all the default values for legacy compatibility
        assert options.stage_all is False
        assert options.group is False
        assert options.interactive is False
        assert options.model is None
        assert options.hint == ""
        assert options.one_liner is False
        assert options.show_prompt is False
        assert options.infer_scope is False
        assert options.require_confirmation is True
        assert options.push is False
        assert options.quiet is False
        assert options.dry_run is False
        assert options.message_only is False
        assert options.verbose is False
        assert options.no_verify is False
        assert options.skip_secret_scan is False
        assert options.language is None
        assert options.hook_timeout == 0

    def test_frozen_dataclass(self):
        """Test that CLIOptions is frozen and immutable."""
        options = CLIOptions()

        with pytest.raises(AttributeError):
            options.quiet = True

    def test_legacy_field_coverage(self):
        """Test that all legacy fields are present."""
        field_names = {f.name for f in fields(CLIOptions)}
        expected_fields = {
            "stage_all",
            "group",
            "interactive",
            "model",
            "hint",
            "one_liner",
            "show_prompt",
            "infer_scope",
            "require_confirmation",
            "push",
            "quiet",
            "dry_run",
            "message_only",
            "verbose",
            "no_verify",
            "skip_secret_scan",
            "language",
            "hook_timeout",
        }
        assert field_names == expected_fields


class TestWorkflowContextIntegration:
    """Integration tests for workflow context objects."""

    def test_options_compatibility(self):
        """Test that options can be created and used together."""
        # Create options for different workflows
        create_opts = PRCreationOptions(draft=True, language="python")
        merge_opts = PRMergeOptions(pr_number=123, merge_method="squash")
        update_opts = PRUpdateOptions(pr_number=456)

        # Verify they don't interfere with each other
        assert create_opts.draft is True
        assert merge_opts.merge_method == "squash"
        assert update_opts.pr_number == 456

        # Test that each has the right structure
        assert hasattr(create_opts, "base_branch")
        assert hasattr(merge_opts, "pr_number")
        assert hasattr(update_opts, "pr_number")

    def test_frozen_immutability(self):
        """Test that all options maintain immutability."""
        # Test PRCreationOptions
        options = PRCreationOptions()
        with pytest.raises(AttributeError):
            options.base_branch = "test"

        # Test PRMergeOptions
        merge_options = PRMergeOptions(pr_number=123)
        with pytest.raises(AttributeError):
            merge_options.pr_number = 999

        # Test PRUpdateOptions
        update_options = PRUpdateOptions(pr_number=456)
        with pytest.raises(AttributeError):
            update_options.pr_number = 999

        # Test CLIOptions
        cli_options = CLIOptions()
        with pytest.raises(AttributeError):
            cli_options.quiet = True

    def test_type_safety(self):
        """Test that types are correctly annotated and enforced."""
        # Test with correct types
        opts = PRMergeOptions(pr_number=123)
        assert isinstance(opts.pr_number, int)

        # Test that default creation works
        create_opts = PRCreationOptions()
        assert isinstance(create_opts.draft, bool)
        assert isinstance(create_opts.hint, str)

    def test_options_equality(self):
        """Test that options with same values are equal."""
        opts1 = PRCreationOptions(draft=True, language="python")
        opts2 = PRCreationOptions(draft=True, language="python")

        # Since they're frozen dataclasses, they should be equal
        assert opts1 == opts2

        # But different options should not be equal
        opts3 = PRCreationOptions(draft=False)
        assert opts1 != opts3

    def test_options_hashing(self):
        """Test that frozen options can be used in sets/dicts."""
        opts1 = PRCreationOptions(draft=True)
        opts2 = PRCreationOptions(draft=True)
        opts3 = PRCreationOptions(draft=False)

        # Should be able to use in sets
        options_set = {opts1, opts2, opts3}
        assert len(options_set) == 2  # opts1 and opts2 are equal

        # Should be able to use as dict keys
        options_dict = {opts1: "value1", opts3: "value2"}
        assert len(options_dict) == 2
        assert options_dict[opts2] == "value1"  # opts2 should map to same as opts1
