"""Tests for the CLI module."""

import pytest
from click.testing import CliRunner

from auto_pr.cli import cli


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Auto-PR" in result.output
        assert "create-pr" in result.output
        assert "merge-pr" in result.output
        assert "update-pr" in result.output

    def test_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_init_help(self, runner):
        """Test init subcommand help."""
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "auto-pr.env" in result.output.lower() or "setup" in result.output.lower()

    def test_model_help(self, runner):
        """Test model subcommand help."""
        result = runner.invoke(cli, ["model", "--help"])
        assert result.exit_code == 0

    def test_config_help(self, runner):
        """Test config subcommand help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    def test_auth_help(self, runner):
        """Test auth subcommand help."""
        result = runner.invoke(cli, ["auth", "--help"])
        assert result.exit_code == 0

    def test_create_pr_help(self, runner):
        """Test create-pr subcommand help."""
        result = runner.invoke(cli, ["create-pr", "--help"])
        assert result.exit_code == 0
        assert "pull request" in result.output.lower()

    def test_merge_pr_help(self, runner):
        """Test merge-pr subcommand help."""
        result = runner.invoke(cli, ["merge-pr", "--help"])
        assert result.exit_code == 0

    def test_update_pr_help(self, runner):
        """Test update-pr subcommand help."""
        result = runner.invoke(cli, ["update-pr", "--help"])
        assert result.exit_code == 0

    def test_language_help(self, runner):
        """Test language subcommand help."""
        result = runner.invoke(cli, ["language", "--help"])
        assert result.exit_code == 0


class TestInitCommand:
    """Test init command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_init_commands(self, monkeypatch):
        def dummy_command(*args, **kwargs):
            pass

        monkeypatch.setattr("auto_pr.init_cli.init.callback", dummy_command)
        monkeypatch.setattr("auto_pr.model_cli.model.callback", dummy_command)
        yield

    def test_init_success(self, runner, monkeypatch, mock_init_commands):
        """Test 'auto-pr init' runs without error when all dependencies succeed."""
        monkeypatch.setattr("rich.console.Console.print", lambda self, *a, **kw: None)
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

    def test_model_success(self, runner, monkeypatch, mock_init_commands):
        """Test 'auto-pr model' runs without error when all dependencies succeed."""
        monkeypatch.setattr("rich.console.Console.print", lambda self, *a, **kw: None)
        result = runner.invoke(cli, ["model"])
        assert result.exit_code == 0
